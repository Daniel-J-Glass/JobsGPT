import time, random, os, csv, platform, sys
import logging
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

from selenium.webdriver.common.action_chains import ActionChains

from bs4 import BeautifulSoup
import pandas as pd
import pyautogui

from urllib.request import urlopen
from webdriver_manager.chrome import ChromeDriverManager
import re
import yaml
from datetime import datetime, timedelta

sys.path.append('../CoverLetterGPT') #Your path to CoverLetterGPT
from CoverLetterGPT import CoverLetterGPT

log = logging.getLogger(__name__)
driver = webdriver.Chrome(ChromeDriverManager().install())
test = True


def setupLogger() -> None:
    dt: str = datetime.strftime(datetime.now(), "%m_%d_%y %H_%M_%S ")

    if not os.path.isdir('./logs'):
        os.mkdir('./logs')

    # TODO need to check if there is a log dir available or not
    logging.basicConfig(filename=('./logs/' + str(dt) + 'applyJobs.log'), filemode='w',
                        format='%(asctime)s::%(name)s::%(levelname)s::%(message)s', datefmt='./logs/%d-%b-%y %H:%M:%S')
    log.setLevel(logging.DEBUG)
    c_handler = logging.StreamHandler()
    c_handler.setLevel(logging.DEBUG)
    c_format = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', '%H:%M:%S')
    c_handler.setFormatter(c_format)
    log.addHandler(c_handler)


class EasyApplyBot:
    setupLogger()
    # MAX_SEARCH_TIME is 10 hours by default, feel free to modify it
    MAX_SEARCH_TIME = 10 * 60 * 60

    def __init__(self,
                 username,
                 password,
                 phone_number,
                 uploads={},
                 filename='output.csv',
                 blacklist=[],
                 blackListTitles=[]) -> None:

        log.info("Welcome to Easy Apply Bot")
        dirpath: str = os.getcwd()
        log.info("current directory is : " + dirpath)

        self.uploads = uploads
        past_ids: list | None = self.get_appliedIDs(filename)
        self.appliedJobIDs: list = past_ids if past_ids != None else []
        self.filename: str = filename
        self.options = self.browser_options()
        self.browser = driver
        self.wait = WebDriverWait(self.browser, 30)
        self.blacklist = blacklist
        self.blackListTitles = blackListTitles
        self.start_linkedin(username, password)
        self.phone_number = phone_number
        self.Resume = None
        self.employment_details = self.uploads["Employment Details"]
        with open(self.employment_details,'r') as f:
            self.details = f.read()

    def get_appliedIDs(self, filename) -> list | None:
        try:
            df = pd.read_csv(filename,
                             header=None,
                             names=['timestamp', 'jobID', 'job', 'company', 'attempted', 'result'],
                             lineterminator='\n',
                             encoding='utf-8')

            df['timestamp'] = pd.to_datetime(df['timestamp'], format="%Y-%m-%d %H:%M:%S")
            df = df[df['timestamp'] > (datetime.now() - timedelta(days=2))]
            jobIDs: list = list(df.jobID)
            log.info(f"{len(jobIDs)} jobIDs found")
            return jobIDs
        except Exception as e:
            log.info(str(e) + "   jobIDs could not be loaded from CSV {}".format(filename))
            return None

    def browser_options(self):
        options = Options()
        options.add_argument("--start-maximized")
        options.add_argument("--ignore-certificate-errors")
        options.add_argument('--no-sandbox')
        options.add_argument("--disable-extensions")

        # Disable webdriver flags or you will be easily detectable
        options.add_argument("--disable-blink-features")
        options.add_argument("--disable-blink-features=AutomationControlled")
        return options

    def start_linkedin(self, username, password) -> None:
        log.info("Logging in.....Please wait :)  ")
        self.browser.get("https://www.linkedin.com/login?trk=guest_homepage-basic_nav-header-signin")
        try:
            user_field = self.browser.find_element("id","username")
            pw_field = self.browser.find_element("id","password")
            login_button = self.browser.find_element("xpath",
                        '//*[@id="organic-div"]/form/div[3]/button')
            user_field.send_keys(username)
            user_field.send_keys(Keys.TAB)
            time.sleep(2)
            pw_field.send_keys(password)
            time.sleep(2)
            login_button.click()
            time.sleep(30)
            # Wait for login verification code, get and insert input.
        except TimeoutException:
            log.info("TimeoutException! Username/password field or login button not found")

    def fill_data(self) -> None:
        self.browser.set_window_size(1, 1)
        self.browser.set_window_position(2000, 2000)

    def start_apply(self, positions, locations) -> None:
        start: float = time.time()
        self.fill_data()

        combos: list = []
        while len(combos) < len(positions) * len(locations):
            position = positions[random.randint(0, len(positions) - 1)]
            location = locations[random.randint(0, len(locations) - 1)]
            combo: tuple = (position, location)
            if combo not in combos:
                combos.append(combo)
                log.info(f"Applying to {position}: {location}")
                location = "&location=" + location
                self.applications_loop(position, location)
            if len(combos) > 500:
                break

    # self.finish_apply() --> this does seem to cause more harm than good, since it closes the browser which we usually don't want, other conditions will stop the loop and just break out

    def applications_loop(self, position, location):
        count_application = 0
        count_job = 0
        jobs_per_page = 0
        start_time: float = time.time()

        log.info("Looking for jobs.. Please wait..")

        self.browser.set_window_position(1, 1)
        self.browser.maximize_window()
        self.browser, _ = self.next_jobs_page(position, location, jobs_per_page)
        log.info("Looking for jobs.. Please wait..")

        while time.time() - start_time < self.MAX_SEARCH_TIME:
            try:
                log.info(f"{(self.MAX_SEARCH_TIME - (time.time() - start_time)) // 60} minutes left in this search")

                # sleep to make sure everything loads, add random to make us look human.
                randoTime: float = random.uniform(3.5, 4.9)
                log.debug(f"Sleeping for {round(randoTime, 1)}")
                time.sleep(randoTime)
                self.load_page(sleep=1)

                # LinkedIn displays the search results in a scrollable <div> on the left side, we have to scroll to its bottom

                # scrollresults = self.browser.find_element(By.CLASS_NAME,
                #     "jobs-search-results-list"
                # )
                # Selenium only detects visible elements; if we scroll to the bottom too fast, only 8-9 results will be loaded into IDs list
                # for i in range(300, 3000, 100):
                #     self.browser.execute_script("arguments[0].scrollTo(0, {})".format(i), scrollresults)

                time.sleep(1)

                # get job links, (the following are actually the job card objects)
                links = self.browser.find_elements("xpath",
                    '//div[@data-job-id]'
                )

                if len(links) == 0:
                    log.debug("No links found")
                    break

                IDs: list = []
                
                # children selector is the container of the job cards on the left
                for link in links:
                    children = link.find_elements("xpath",
                        '//ul[@class="scaffold-layout__list-container"]'
                    )
                    for child in children:
                        if child.text not in self.blacklist:
                            temp = link.get_attribute("data-job-id")
                            jobID = temp.split(":")[-1]
                            IDs.append(int(jobID))
                IDs: list = set(IDs)

                # remove already applied jobs
                before: int = len(IDs)
                jobIDs: list = [x for x in IDs if x not in self.appliedJobIDs]
                after: int = len(jobIDs)

                # it assumed that 25 jobs are listed in the results window
                if len(jobIDs) == 0 and len(IDs) > 23:
                    jobs_per_page = jobs_per_page + 25
                    count_job = 0
                    self.avoid_lock()
                    self.browser, jobs_per_page = self.next_jobs_page(position,
                                                                    location,
                                                                    jobs_per_page)
                # loop over IDs to apply
                for i, jobID in enumerate(jobIDs):
                    count_job += 1
                    self.get_job_page(jobID)

                    # get easy apply button
                    button = self.get_easy_apply_button()
                    # word filter to skip positions not wanted

                    if button is not False:
                        if any(word in self.browser.title for word in blackListTitles):
                            log.info('skipping this application, a blacklisted keyword was found in the job position')
                            string_easy = "* Contains blacklisted keyword"
                            result = False
                        else:
                            # extracting job description
                            job_description = self.get_job_description()
                            self.Resume = CoverLetterGPT(job_description,self.uploads['Resume'])

                            string_easy = "* has Easy Apply Button"
                            log.info("Clicking the EASY apply button")
                            button.click()
                            time.sleep(3)
                            self.fill_out_phone_number()
                            result: bool = self.send_resume()
                            count_application += 1
                    else:
                        log.info("The button does not exist.")
                        string_easy = "* Doesn't have Easy Apply Button"
                        result = False

                    position_number: str = str(count_job + jobs_per_page)
                    log.info(f"\nPosition {position_number}:\n {self.browser.title} \n {string_easy} \n")

                    self.write_to_file(button, jobID, self.browser.title, result)

                    # sleep every 20 applications
                    if count_application != 0 and count_application % 20 == 0:
                        sleepTime: int = random.randint(500, 900)
                        log.info(f"""********count_application: {count_application}************\n\n
                                    Time for a nap - see you in:{int(sleepTime / 60)} min
                                ****************************************\n\n""")
                        time.sleep(sleepTime)

                    # go to new page if all jobs are done
                    if count_job == len(jobIDs):
                        jobs_per_page = jobs_per_page + 25
                        count_job = 0
                        log.info("""****************************************\n\n
                        Going to next jobs page, YEAAAHHH!!
                        ****************************************\n\n""")
                        self.avoid_lock()
                        self.browser, jobs_per_page = self.next_jobs_page(position,
                                                                        location,
                                                                        jobs_per_page)
            except Exception as e:
                print(e)

    def write_to_file(self, button, jobID, browserTitle, result) -> None:
        def re_extract(text, pattern):
            target = re.search(pattern, text)
            if target:
                target = target.group(1)
            return target

        timestamp: str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        attempted: bool = False if button == False else True
        job = re_extract(browserTitle.split(' | ')[0], r"\(?\d?\)?\s?(\w.*)")
        company = re_extract(browserTitle.split(' | ')[1], r"(\w.*)")

        toWrite: list = [timestamp, jobID, job, company, attempted, result]
        with open(self.filename, 'a') as f:
            writer = csv.writer(f)
            writer.writerow(toWrite)

    def get_job_page(self, jobID):

        job: str = 'https://www.linkedin.com/jobs/view/' + str(jobID)
        self.browser.get(job)
        self.job_page = self.load_page(sleep=0.5)
        return self.job_page

    def get_easy_apply_button(self):
        print("Easy Apply")
        try:
            button = self.browser.find_elements("xpath",
                '//button[contains(@class, "jobs-apply-button")]'
            )

            EasyApplyButton = button[0]
            
        except Exception as e: 
            print("Exception:",e)
            EasyApplyButton = False

        return EasyApplyButton

    def get_job_description(self):
        try:
            job_description_element = self.wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".jobs-description-content__text"))
            )
            job_description = job_description_element.find_element(By.CSS_SELECTOR,"span").get_attribute("innerHTML")
            job_description = re.sub(r'<[^>]+>', ' ', job_description)
            job_description = re.sub(r'\xa0', ' ', job_description)
            job_description = re.sub(r'<!---->', ' ', job_description)
            job_description = re.sub(r'\s+', ' ', job_description).strip()
        except:
            job_description = ""

        return job_description

    def fill_out_phone_number(self):
        def is_present(button_locator) -> bool:
            return len(self.browser.find_elements(button_locator[0], button_locator[1])) > 0

        next_locator = (By.CSS_SELECTOR, "button[aria-label='Continue to next step']")

        input_field = self.browser.find_element('xpath', "//input[contains(@id, 'phoneNumber')]")

        if input_field:
            input_field.clear()
            input_field.send_keys(self.phone_number)
            time.sleep(random.uniform(4.5, 6.5))

            next_locator = (By.CSS_SELECTOR, "button[aria-label='Continue to next step']")
            error_locator = (By.CSS_SELECTOR, "p[data-test-form-element-error-message='true']")

            # Click Next or submit button if possible
            button = None
            if is_present(next_locator):
                button = self.wait.until(EC.element_to_be_clickable(next_locator))

            if is_present(error_locator):
                for element in self.browser.find_elements(error_locator[0], error_locator[1]):
                    text = element.text
                    if "Please enter a valid answer" in text:
                        button = None
                        break
            if button:
                button.click()
                time.sleep(random.uniform(1.5, 2.5))

        else:
            log.debug("Could not find phone number field")

    def fill_out_information(self):
        """
        Identify response fields on a page, classify them as either multiple choice or text input/dropdown, and extract the response.
        """
        response_list = []
        sections = self.browser.find_elements(By.CSS_SELECTOR, 'div.jobs-easy-apply-form-section__grouping')
        log.info("Answering {} sections".format(len(sections)))
        for section in sections:
            try:
                # Check if the response field is a multiple choice question
                radio_options = section.find_elements(By.CSS_SELECTOR, 'input[type=radio]')
                checkbox_options = section.find_elements(By.CSS_SELECTOR, 'input[type=checkbox]')
                # Check if the response field is a text input or select dropdown
                text_inputs = section.find_elements(By.CSS_SELECTOR, 'input[type=text]')
                dropdowns = section.find_elements(By.CSS_SELECTOR, 'select')
                single_typeahead_entity_form = section.find_elements(By.CSS_SELECTOR, '.search-basic-typeahead input[type=text]')

                if radio_options:
                    question = section.find_element(By.CSS_SELECTOR, 'legend').text.strip()
                    options = {}
                    for option in radio_options:
                        option_text = option.find_element(By.XPATH, './following-sibling::label').text
                        options[option_text] = option
                    response_list.append(("multiple_choice", {"question": question, "options": options}))
                    
                elif checkbox_options:
                    question = section.find_element(By.CSS_SELECTOR, 'legend').text.strip()
                    options = {}
                    for option in checkbox_options:
                        option_text = option.find_element(By.XPATH, './following-sibling::label').text
                        options[option_text] = option
                    response_list.append(("checkbox", {"question": question, "options": options}))

                elif text_inputs:
                    for input_field in text_inputs:
                        label_element = input_field.find_element(By.XPATH, './preceding-sibling::label')
                        if label_element:
                            label = label_element.text.strip()
                        else:
                            label = ""
                        response_list.append(("text_entry", {"label": label, "input": input_field}))

                elif dropdowns:
                    for dropdown_field in dropdowns:
                        label_element = dropdown_field.find_element(By.XPATH, './preceding-sibling::label')
                        if label_element:
                            label = label_element.text.strip()
                        else:
                            label = ""
                        response_list.append(("dropdown", {"label": label, "dropdown": dropdown_field}))
                
                elif single_typeahead_entity_form:
                    question = section.find_element(By.CSS_SELECTOR, 'label[for*="-city-"]').text.strip()
                    input_field = section.find_element(By.CSS_SELECTOR, 'input[type=text]')
                    response_list.append(("text_entry", {"label": question, "input": input_field}))

                else:
                    continue
                
            except NoSuchElementException:
                continue

        # Input the extracted responses
        for response in response_list:
            if response[0] == "multiple_choice":
                if not self.input_radio_options(response[1]["question"], response[1]["options"]):
                    return False
            elif response[0] == "checkbox":
                if not self.input_checkbox_options(response[1]["question"], response[1]["options"]):
                    return False
            elif response[0] == "text_entry":
                if not self.input_information(response[1]["label"], response[1]["input"]):
                    return False
            elif response[0] == "dropdown":
                if not self.select_dropdown(response[1]["label"], response[1]["dropdown"]):
                    return False
                    
            time.sleep(random.uniform(.5, 1.5))

        return True

    def input_radio_options(self, question, options):
        """Takes in radio option questions and options and asks self.resume to answer the question

        Args:
            question (str): The question being asked.
            options (dict): A dictionary containing the text of the options as keys and the corresponding WebElement as values.
        """
        prompt = f"Extra details: {self.details}\n\
        Q: {question}\nOptions: {options.keys()}\nThe following is only the correct option based on the prior details. No other outputs.:"
        
        answer = self.Resume.ask(prompt)
        print("Answer:"+answer)
        # Find the selected option and click on its input element
        selected_option = options.get(answer)
        for _ in range(3):  # Retry up to three times
            if selected_option:
                break
            answer = self.Resume.ask(prompt)
            print(answer)
            selected_option = options.get(answer)

        if selected_option:
            print(selected_option)
            actions = ActionChains(driver)
            actions.move_to_element(selected_option).click().perform()

            return True
        
        else:
            return False

    def input_information(self, label, input):
        """Takes in a text input question and asks self.resume to answer the question

        Args:
            label (str): The label for the text input field.
            input (WebElement): The WebElement for the text input field.
        """
        # Check if the input field already has a value
        if input.get_attribute("value"):
            return True

        prompt = f"Extra Details: {self.details}\n\
        The following is the answer to the prompt for answering professional details according to \"extra details\" and \"resume details\".\
        Is the skill listed? If not, answer 0 years of experience if it is not in the prior details. Makes very conservative estimates of related skills.\
        If the prompt asks for a number, only outputs a number. Answers accurately about personal details like location and relevant websites.{label}:"
        answer = self.Resume.ask(prompt)

        if re.search(r'\d', answer):
            answer = re.findall(r'\d+(?:\.\d*)?', answer)[0]
        # fill in input with answer
        input.clear()
        input.send_keys(answer)
        return True

    def select_dropdown(self, label, dropdown):
        """Takes in a dropdown question and asks self.resume to answer the question

        Args:
            label (str): The label for the dropdown field.
            dropdown (WebElement): The WebElement for the dropdown field.
        """
        # get all dropdown options
        options = dropdown.find_elements(By.CSS_SELECTOR, 'option')
        option_texts = [option.text for option in options]

        prompt = f"Extra details: {self.details}\n\
            Based on these details, the following is the best option for the question.\n\
            Q: {label} Options: {option_texts}\n\
            The correct option is (no extra words):"
        
        for _ in range(2):
            answer = self.Resume.ask(prompt)
            
            for option in options:
                if option.text in answer:
                    option.click()
                    return True
                
        return False

        


    def send_resume(self) -> bool:
        def is_present(button_locator) -> bool:
            return len(self.browser.find_elements(button_locator[0],
                                                  button_locator[1])) > 0

        try:
            time.sleep(random.uniform(1.5, 2.5))

            next_locater = (By.CSS_SELECTOR,
                            "button[aria-label='Continue to next step']")
            review_locater = (By.CSS_SELECTOR,
                            "button[aria-label='Review your application']")
            submit_locater = (By.CSS_SELECTOR,
                            "button[aria-label='Submit application']")
            submit_application_locator = (By.CSS_SELECTOR,
                                        "button[aria-label='Submit application']")
            
            error_locator = (By.CSS_SELECTOR, "div.artdeco-inline-feedback--error span.artdeco-inline-feedback__message")
            
            upload_locator = (By.CSS_SELECTOR, "input[name='file']")
            follow_locator = (By.CSS_SELECTOR, "label[for='follow-company-checkbox']")

            question_locators = [(By.CSS_SELECTOR, "input[type='text']"), (By.CSS_SELECTOR, "input[type='email']"), (By.CSS_SELECTOR, "input[type='tel']"), (By.CSS_SELECTOR, "input[type='radio']")]


            submitted = False
            while True:
                #updating details for updating knowledge base realtime
                with open(self.employment_details,'r') as f:
                    self.details = f.read()
                # Upload Cover Letter if possible
                if is_present(upload_locator):

                    input_buttons = self.browser.find_elements(upload_locator[0],
                                                               upload_locator[1])
                    for input_button in input_buttons:
                        parent = input_button.find_element(By.XPATH, "..")
                        sibling = parent.find_element(By.XPATH, "preceding-sibling::*")
                        grandparent = sibling.find_element(By.XPATH, "..")
                        for key in self.uploads.keys():
                            sibling_text = sibling.text
                            gparent_text = grandparent.text
                            if key.lower() in sibling_text.lower() or key in gparent_text.lower():
                                print(key.lower())
                                if "cover" in key.lower():
                                    self.Resume.generate_cover_letter(self.uploads['Cover Letter'])
                                input_button.send_keys(self.uploads[key])

                    # input_button[0].send_keys(self.cover_letter_loctn)
                    time.sleep(random.uniform(4.5, 6.5))

                # Click Next or submitt button if possible
                button: None = None
                buttons: list = [next_locater, review_locater, follow_locator,
                           submit_locater, submit_application_locator]
                for i, button_locator in enumerate(buttons):
                    print(button_locator)
                    if is_present(button_locator):
                        button: None = self.wait.until(EC.element_to_be_clickable(button_locator))

                    if is_present(error_locator):
                        # Check for presence of input fields if it errors on next
                        if button_locator in [next_locater, review_locater]:
                            print("Question Page")
                            for question_locator in question_locators:
                                if is_present(question_locator):
                                    print("Questions present")
                                    success = self.fill_out_information()
                                    time.sleep(1)
                                    break
                                    
                        if not success:
                            button = None
                            break
                   
                    if test and button and i in (3,4):
                        while is_present(submit_application_locator) or is_present(submit_locater):
                            time.sleep(5)
                        break

                    if button:
                        button.click()
                        time.sleep(random.uniform(1.5, 2.5))
                        if i in (3, 4):
                            submitted = True
                        if i != 2:
                            break
                        
                if button == None: # Catches if next doesn't work
                    log.info("Could not complete submission")
                    break
                elif submitted:
                    log.info("Application Submitted")
                    break

            time.sleep(random.uniform(1.5, 2.5))


        except Exception as e:
            log.info(e)
            log.info("cannot apply to this job")
            raise (e)

        return submitted

    def load_page(self, sleep=1):
        scroll_page = 0
        while scroll_page < 4000:
            self.browser.execute_script("window.scrollTo(0," + str(scroll_page) + " );")
            scroll_page += 200
            time.sleep(sleep)

        if sleep != 1:
            self.browser.execute_script("window.scrollTo(0,0);")
            time.sleep(sleep * 3)

        print("Page loaded.")
        page = BeautifulSoup(self.browser.page_source, "lxml")
        return page

    def extract_radio_options(self, parent_element=None) -> dict:
        # Define a dictionary to store the questions and their options
        questions = {}

        # Find all the fieldsets that contain the radio button options
        if parent_element:
            option_fieldsets = parent_element.find_elements(By.CSS_SELECTOR, 'fieldset[data-test-form-builder-radio-button-form-component]')
        else:
            option_fieldsets = self.driver.find_elements(By.CSS_SELECTOR, 'fieldset[data-test-form-builder-radio-button-form-component]')

        # Loop through the fieldsets and extract the question and its options
        for option_fieldset in option_fieldsets:
            # Get the question text from the legend element
            question = option_fieldset.find_element(By.CSS_SELECTOR, 'legend[data-test-form-builder-radio-button-form-component__title]').text

            # Get the options by finding all the input elements within the fieldset
            options = {}
            option_inputs = option_fieldset.find_elements(By.CSS_SELECTOR, 'input[type="radio"]')
            for option_input in option_inputs:
                option_text = option_input.find_element(By.XPATH, './following-sibling::label').text
                options[option_text] = option_input

            # Add the question and its options to the questions dictionary
            questions[question] = options

        return questions


    def avoid_lock(self) -> None:
        x, _ = pyautogui.position()
        pyautogui.moveTo(x + 200, pyautogui.position().y, duration=1.0)
        pyautogui.moveTo(x, pyautogui.position().y, duration=0.5)
        pyautogui.keyDown('ctrl')
        pyautogui.press('esc')
        pyautogui.keyUp('ctrl')
        time.sleep(0.5)
        pyautogui.press('esc')

    def next_jobs_page(self, position, location, jobs_per_page):
        self.browser.get(
            "https://www.linkedin.com/jobs/search/?f_LF=f_AL&keywords=" +
            position + location + "&start=" + str(jobs_per_page))
        self.avoid_lock()
        log.info("Lock avoided.")
        self.load_page()
        return (self.browser, jobs_per_page)

    def finish_apply(self) -> None:
        self.browser.close()


if __name__ == '__main__':

    with open("config.yaml", 'r') as stream:
        try:
            parameters = yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            raise exc

    assert len(parameters['positions']) > 0
    assert len(parameters['locations']) > 0
    assert parameters['username'] is not None
    assert parameters['password'] is not None
    assert parameters['phone_number'] is not None

    if 'uploads' in parameters.keys() and type(parameters['uploads']) == list:
        raise Exception("uploads read from the config file appear to be in list format" +
                        " while should be dict. Try removing '-' from line containing" +
                        " filename & path")

    log.info({k: parameters[k] for k in parameters.keys() if k not in ['username', 'password']})

    output_filename: list = [f for f in parameters.get('output_filename', ['output.csv']) if f != None]
    output_filename: list = output_filename[0] if len(output_filename) > 0 else 'output.csv'
    blacklist = parameters.get('blacklist', [])
    blackListTitles = parameters.get('blackListTitles', [])

    uploads = {} if parameters.get('uploads', {}) == None else parameters.get('uploads', {})
    for key in uploads.keys():
        assert uploads[key] != None

    bot = EasyApplyBot(parameters['username'],
                       parameters['password'],
                       parameters['phone_number'],
                       uploads=uploads,
                       filename=output_filename,
                       blacklist=blacklist,
                       blackListTitles=blackListTitles
                       )

    locations: list = [l for l in parameters['locations'] if l != None]
    positions: list = [p for p in parameters['positions'] if p != None]
    bot.start_apply(positions, locations)
