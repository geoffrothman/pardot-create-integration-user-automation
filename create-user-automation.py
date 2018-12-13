from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import requests
import time
import csv
import base64
import os
from base64 import b64decode, b64encode
import boto3

os.environ["PATH"] += os.pathsep + r'/Users/skasula/Downloads'


# Add script to:
#
# 1. Login as admin - login_as_pardot_admin()
# 2. Login to customer Pardot's org - connect_to_account()
# 3. Create custom role - upset_configuration_value(),  upsert_role_permisions()
# 4. Create custom user using the role - create_integration_user()
# 5. Setup limits - update_limits()
# 6. create Jungle entry for connecting to pardot org


ingeration_role_name = "B2B Marketing Integration User"
increase_request_size = "api.enable_larger_bulk_data_limit"
enable_custom_role = "enable_custom_roles_for_super_user"
config_name = enable_custom_role

properties = {'checkallviewmarketing':True, 'checks_prospects__prospects__viewnotassigned':True, 'checks_prospects__visitors__view':True, 'checks_prospects__lifecycle__viewreport':True, 'prospects__prospectaccounts__view':True}

# Usage:
# new_account_id = "36862"
# config_new_account(new_account_id)
# config_new_account("82202")

# configute_account(account_id, integration_role_name) - to be removed


# Main Method: To Create new Pardot Integration User Steps
def config_new_account(new_account_id):
    browser = webdriver.Chrome()
    login_as_pardot_admin(browser)
    connect_to_account(browser, new_account_id)

    upset_configuration_value(browser, increase_request_size, True)
    upset_configuration_value(browser, enable_custom_role, True)

    upsert_role_permisions(browser, properties)

    update_limits(browser) # limits set are at account level

    create_integration_user(browser, new_account_id, "B2B Marketing Integration User")

    return browser


# Step1 - to login as pardot admin - account level
def login_as_pardot_admin(browser):
    browser.get('https://pi.pardot.com/user/login')

    email_input = browser.find_element_by_id('email_address')
    email_input.send_keys("skasula+pardot@salesforce.com")

    password = browser.find_element_by_id('password')
    password.send_keys('xxxx')

    browser.find_element_by_name('commit').click()

    WebDriverWait(browser, 30).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "#agency_form > div.k-content > span > span"))
    )


# Step2 - After logged in as admin user, connect to any pilot account/org - with pardot account number
# search on the browser
def connect_to_account(browser, account_id):
    print("********* Connecting to Account Id: {} *********".format(account_id))
    browser.get('https://pi.pardot.com/')

    account_selector = WebDriverWait(browser, 30).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "#agency_form > div.k-content > span > span"))
    )

    account_selector.click()

    search_input = WebDriverWait(browser, 30).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "#dropdown_agency_account_id-list > span > input"))
    )

    time.sleep(5)
    search_input.send_keys(account_id)
    #wait for some result
    WebDriverWait(browser, 30).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "#dropdown_agency_account_id_listbox > li:nth-child(2)"))
    )

    account = WebDriverWait(browser, 30).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "#dropdown_agency_account_id_listbox"))
    )

    lis = account.find_elements_by_tag_name("li")

    #find exact account
    for li in lis:
        if("/{})".format(account_id) in li.text):
            print("Account shard/id: {}".format(li.text))
            li.click()

    # WebDriverWait(browser, 30).until(
    #     EC.presence_of_element_located((By.ID, "enablement-modal-trigger"))
    # )
    print("********* Connected to Account Id: {} *********".format(account_id))

#admin_btn = browser.find_element_by_css_selector("#admin-tog > i")

# Step3
def upset_configuration_value(browser, config_name, value):

    browser.get("https://pi.pardot.com/accountSetting")

    filter_input = WebDriverWait(browser, 30).until(
        EC.presence_of_element_located((By.NAME, "text_filter"))
    )

    filter_input.send_keys(config_name)

    config_item = WebDriverWait(browser, 30).until(
             EC.presence_of_element_located((By.CSS_SELECTOR, "[data-settingkey='feature.{}']".format(config_name)))
        )


    if (config_item.find_element_by_tag_name('img').is_displayed() != value):

        config_item.click()

        config_item = WebDriverWait(browser, 30).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "[data-settingkey='feature.{}']".format(config_name)))
        )

        config_item.click()

        #or config_item.click()
        WebDriverWait(browser, 30).until(EC.alert_is_present())
        browser.switch_to_alert().accept()

        time.sleep(5)  # wait  sec to change to take effect
        print("Updating configuration {} to: {}".format(config_name, value))
    else:
        print("Configuration {} is already set to: {}, skipping update".format(config_name, value))

# Step3.1
def upsert_role_permisions(browser, properties):

    browser.get('https://pi.pardot.com/role')

    link = None

    try:
        link = WebDriverWait(browser, 10).until(
            EC.presence_of_element_located((By.PARTIAL_LINK_TEXT, 'B2B Marketing Integration User'))
        )
    except TimeoutException:
        pass

    if (link != None):
        print("Role already exists, updating")
        role_url = link.get_attribute('href')
        role_edit_url = role_url.replace("read", "edit")
        print("Updating role: {}".format(role_edit_url))
        browser.get(role_edit_url)
    else:
        print("Role does not exist, creating new one")
        browser.get('https://pi.pardot.com/role/create')

        name_input = browser.find_element_by_id("name")
        name_input.send_keys("B2B Marketing Integration User")

    for (checkbox_id, value) in properties.items():

        checkbox =  WebDriverWait(browser, 30).until(
            EC.presence_of_element_located((By.ID, checkbox_id))
        )
        #move to Prospects tab

        if ("prospects" in checkbox_id):
            browser.find_element_by_css_selector("#ro_form_update > form > ul > li:nth-child(2) > a").click()
            time.sleep(2)

        if (checkbox.is_selected() != value):
            print("{} valuewill be set to: {}, not changing.".format(checkbox_id, value))
            time.sleep(2)
            checkbox.click()
        else:
            print("{} already has value: {}, not changing.".format(checkbox_id, value))

    browser.find_element_by_name("commit").click()


# Step 4
def update_limits(browser):
    browser.get("https://pi.pardot.com/account")

    edit_btn = WebDriverWait(browser, 30).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "#header-actions > ul > a:nth-child(1)"))
    )
    time.sleep(2)

    edit_btn.click()
    time.sleep(2)

    account_limit_expend = WebDriverWait(browser, 30).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "#toggle-account-limits"))
    )

    account_limit_expend.click()
    time.sleep(2)

    max_requests_day = browser.find_element_by_id("max_api_requests")
    max_requests_day.clear()
    max_requests_day.send_keys(1000000)
    print("Updated max_requests_day to 1000000")

    time.sleep(2)

    concurrent_api_requests = browser.find_element_by_id("concurrent_api_requests")
    concurrent_api_requests.clear()
    concurrent_api_requests.send_keys(10)
    print("Updated concurrent_api_requests to 10")

    time.sleep(2)

    browser.find_element_by_name("commit").click()


# Step 5
def create_integration_user(browser, account_id, ingeration_role_name):
    browser.get("https://pi.pardot.com/user/create")
    first_name_input = browser.find_element_by_name("first_name")
    first_name_input.send_keys("B2B Marketing")

    last_name_input = browser.find_element_by_name("last_name")
    last_name_input.send_keys("Integration User")

    username = browser.find_element_by_name("username")
    username.send_keys("skasula+{}@salesforce.com".format(account_id))

    el = browser.find_element_by_name('role')
    for option in el.find_elements_by_tag_name('option'):
        if option.text == ingeration_role_name:
            option.click()  # select() in earlier versions of webdriver
            break

    #check this section
    timezone_id = WebDriverWait(browser, 30).until(
        EC.presence_of_element_located((By.ID, "timezone_id"))
    )
    for option in timezone_id.find_elements_by_tag_name('option'):
        if option.text == '(GMT) UTC':
            option.click()  # select() in earlier versions of webdriver
            break

    browser.find_element_by_name("commit").click()


# Steps to update accounts - login as admin, connect to account, update_limits
def update_accounts(account_ids):

    for account_id in account_ids:
        browser = webdriver.Chrome()
        login_as_pardot_admin(browser)

        print("********* Working on Account Id: {} *********".format(account_id))
        connect_to_account(browser, account_id)
        update_limits(browser)
        print("********* Done for Account Id: {} *********".format(account_id))
        browser.quit()

# Example
# browser = debug_account("492861")
def debug_account(account_id):
    browser = webdriver.Chrome()
    login_as_pardot_admin(browser)
    connect_to_account(browser, account_id)
    return browser


def get_puller_creds(filename_and_path):
    result = []
    with open(filename_and_path) as tsvfile:
        tsvreader = csv.reader(tsvfile, delimiter="\t")
        for line in tsvreader:

            account_number = line[0]
            username = line[1]
            password = line[2]
            api_key = line[3]
            cred = {"org_name": account_number, "username": username, "password": password, "api_key": api_key}
            print(cred)
            result.append(cred)

    return result

creds = get_puller_creds('/Users/skasula/Documents/Projects/pardot.tsv')


def login_as_pardot_user(browser, username, passwd):
    browser.get('https://pi.pardot.com/user/login')

    email_input = browser.find_element_by_id('email_address')
    email_input.send_keys(username)

    password = browser.find_element_by_id('password')
    password.send_keys(passwd)

    browser.find_element_by_name('commit').click()

# Update UTC time
def update_timezone_to_utc(browser, password_, username_):
    login_as_pardot_user(browser, username_, password_)
    browser.get('https://pi.pardot.com/account/user')
    browser.find_element_by_css_selector('#header-actions > ul > a:nth-child(1)').click()
    timezone_id = WebDriverWait(browser, 30).until(
        EC.presence_of_element_located((By.ID, "timezone_id"))
    )
    for option in timezone_id.find_elements_by_tag_name('option'):
        if option.text == '(GMT) UTC':
            option.click()  # select() in earlier versions of webdriver
            break
    browser.find_element_by_name('commit').click()


def check_pardot_integration_user():
    for cred in creds:
        print(cred['org_name'])
        res = check_api_call(cred['username'], cred['password'], cred['api_key'])
        print(res.text)


def check_api_call(email, password, user_key):
    url = "https://pi.pardot.com/api/login/version/3"

    payload = "------WebKitFormBoundary7MA4YWxkTrZu0gW\r\nContent-Disposition: form-data; name=\"user_key\"\r\n\r\n{}\r\n------WebKitFormBoundary7MA4YWxkTrZu0gW\r\nContent-Disposition: form-data; name=\"password\"\r\n\r\n{}\r\n------WebKitFormBoundary7MA4YWxkTrZu0gW\r\nContent-Disposition: form-data; name=\"email\"\r\n\r\n{}\r\n------WebKitFormBoundary7MA4YWxkTrZu0gW--".format(user_key, password, email)
    headers = {
        'content-type': "multipart/form-data; boundary=----WebKitFormBoundary7MA4YWxkTrZu0gW",
        'cache-control': "no-cache",
        'postman-token': "4a740fdd-7324-2f54-5411-8345931584c0"
    }

    response = requests.request("POST", url, data=payload, headers=headers)
    return response



#browser = debug_account('153261')
#update_accounts(['492861'])
#browser = config_new_account('189272')

prod_key = 'a04b2ac9-1b8f-4586-b556-d8b46c433bd5'


def printJunglePardotConfig(tenant_id):
    tenant_creds = [c for c in creds if tenant_id in c['username']]
    if len(tenant_creds) == 1:
        creds_ = tenant_creds[0]
        org_name, username, password, api_key = creds_['org_name'], creds_['username'], creds_['password'], creds_['api_key']
        print("Creds for org: {}".format(org_name))
        encrypted_key = encryptWithProdKey(username, password, api_key)

        payload = '''"pardot":{
    "fetch_data":true,
    "encrypted_credentials":"%s"
  },''' % (encrypted_key)

        print(payload)


def encryptWithProdKey(username, password, api_key):
    payload = '''{                                     
"pardot_email":"%s",
"pardot_password":"%s",
"pardot_user_key":"%s"
 }''' % (username, password, api_key)

    session = boto3.Session(profile_name='implisit')
    kms = session.client('kms', region_name='us-west-2')

    stuff = kms.encrypt(KeyId='arn:aws:kms:us-west-2:187473451979:key/a04b2ac9-1b8f-4586-b556-d8b46c433bd5', Plaintext=payload)

    binary_encrypted = stuff[u'CiphertextBlob']
    encrypted = b64encode(binary_encrypted)

    binary_data = base64.b64decode(encrypted)
    meta = kms.decrypt(CiphertextBlob=binary_data)
    plaintext = meta[u'Plaintext']
    assert plaintext.decode() == payload

    return encrypted.decode()


# this method is read the configurations - NOT USED ANYWHERE
def find_item(browser, config_name):

    browser.get("https://pi.pardot.com/accountSetting")

    filter_input = WebDriverWait(browser, 30).until(
        EC.presence_of_element_located((By.NAME, "text_filter"))
    )

    filter_input.send_keys(config_name)

    config_item = WebDriverWait(browser, 30).until(
             EC.presence_of_element_located((By.CSS_SELECTOR, "[data-settingkey='feature.{}']".format(config_name)))
        )

    time.sleep(5)

# NOT Called anywhere
def increase_records_per_request():
    "api.enable_larger_bulk_data_limit"
    pass

