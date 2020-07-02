import re
import io
import os
import threading
import shutil
import time
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By

MERGED_FILE_FOLDER = "temp1"
BLOCK_TRANSLATED_FOLDER = "temp2"
MERGED_RPY_FILE = "temp.txt"
MERGED_BLOCK_FILE = "output-temp.txt"
SIGN_BREAK_FILE = "ThisIsSomeRandomString"
MAX_CHAR_IN_THREAD = 1000
MAX_TIME_WAIT_ELEMENT = 3
DRIVER_PATH = "Driver/chromedriver.exe"
LANGUAGE_SUPPORT = ["af", "sq", "am", "ar", "hy", "az", "eu", "be", "bn", "bs", "bg", "ca", "ceb", "zh-CN", "zh-TW", "co", "hr", "cs",
                    "da", "nl", "en", "eo", "et", "fi", "fr", "fy", "gl", "ka", "de", "el", "gu", "ht", "ha", "haw", "he", "hi", "hmn",
                    "hu", "is", "ig", "id", "ga", "it", "ja", "jv", "kn", "kk", "km", "rw", "ko", "ku", "ky", "lo", "la", "lv", "lt",
                    "lb", "mk", "mg", "ms", "ml", "mt", "mi", "mr", "mn", "my", "ne", "no", "ny", "or", "ps", "fa", "pl", "pt", "pa",
                    "ro", "ru", "sm", "gd", "sr", "st", "sn", "sd", "si", "sk", "sl", "so", "es", "su", "sw", "sv", "tl", "tg", "ta",
                    "tt", "te", "th", "tr", "tk", "uk", "ur", "ug", "uz", "vi", "cy", "xh", "yi", "yo", "zu"]
current_location = None
lock = threading.Lock()
dialogue_thread_done = []
total_cluster_translate = []
# Build option
WEB_DRIVER_OPTIONS = webdriver.ChromeOptions()
WEB_DRIVER_OPTIONS.add_argument("--no-sandbox")
WEB_DRIVER_OPTIONS.add_argument("--disable-gpu")
WEB_DRIVER_OPTIONS.add_argument("--log-level=3")
WEB_DRIVER_OPTIONS.add_argument("--disable-extensions")
WEB_DRIVER_OPTIONS.add_argument("disable-infobars")


class CurrentLocation:
    def __init__(self, index, offset):
        self.index = index
        self.offset = offset


class ClusterUnit:
    def __init__(self, before_translate, after_translate):
        self.before_translate = before_translate
        self.after_translate = after_translate


class LineUnit:
    def __init__(self, raw_text, translated_text, clusters_unit):
        self.raw_text = raw_text
        self.translated_text = translated_text
        self.clusters_unit: ClusterUnit = clusters_unit


class BlockUnit:
    def __init__(self, index, raw_text, lines_unit):
        self.index = index
        self.raw_text = raw_text
        self.lines_unit: LineUnit = lines_unit


def clear_console():
    # TODO check system is linux
    return os.system('cls')


def is_directory_exists(directory_path):
    return os.path.exists(directory_path)


def get_rpy_files_in_directory(directory_path):
    files = []
    for f in os.listdir(directory_path):
        full_path = os.path.join(directory_path, f)
        if os.path.isfile(full_path) and f.endswith(".rpy"):
            files.append(full_path)
    return files


def merge_files(files):
    with open("{}\\{}".format(MERGED_FILE_FOLDER, MERGED_RPY_FILE), "w", encoding="utf-8") as temp_file:
        for file in files:
            temp_file.write("{}{}{}\n".format(
                SIGN_BREAK_FILE, file, SIGN_BREAK_FILE))
            with open(file, "r", encoding="utf8") as f:
                for line in f:
                    temp_file.write(line)
            temp_file.write("{}\n".format(SIGN_BREAK_FILE))


def count_substring_in_string(sub, str):
    return str.count(sub)


def get_content_from_raw(raw_line):
    result = ""
    is_start = False
    for i in range(len(raw_line), 0, -1):
        if raw_line[i-1] == '"':
            if not is_start:
                is_start = True
                continue
            if raw_line[i-2] != '\\':
                return result[::-1].replace('\n', '')
        result += raw_line[i-1]


def break_clusters(content):
    clusters_unit = []
    # break trans obj
    temp = ""
    stop_scan_type = None
    for i in range(len(content)):
        if stop_scan_type is None:
            if content[i] == "[":
                stop_scan_type = 1
            if content[i] == "{":
                stop_scan_type = 2
            if content[i] == "\\" and content[i+1] == '"':
                stop_scan_type = 3
            if content[i] == "\\" and content[i+1] == "[":
                stop_scan_type = 4
            if content[i] == "\\" and content[i+1] == "]":
                stop_scan_type = 5
            if content[i] == "\\" and content[i+1] == "{":
                stop_scan_type = 6
            if content[i] == "\\" and content[i+1] == "}":
                stop_scan_type = 7
            if len(content) >= 2 and content[i] == "%" and content[i+1] != ".":
                stop_scan_type = 8
            if len(content) >= 4 and content[i] == "%" and content[i+1] == ".":
                stop_scan_type = 9
            if content[i] == "\\" and content[i+1] == "n":
                stop_scan_type = 10
            if stop_scan_type is not None:
                if temp != "":
                    clusters_unit.append(ClusterUnit(temp.strip(), None))
                    temp = ""
                continue
        else:
            if (stop_scan_type == 1 and content[i] == "]") or (stop_scan_type == 2 and content[i] == "}") \
                    or (stop_scan_type == 3 and content[i-1] == "\\" and content[i] == '"') \
                    or (stop_scan_type == 4 and content[i-1] == "\\" and content[i] == '[') \
                    or (stop_scan_type == 5 and content[i-1] == "\\" and content[i] == ']') \
                    or (stop_scan_type == 6 and content[i-1] == "\\" and content[i] == '{') \
                    or (stop_scan_type == 7 and content[i-1] == "\\" and content[i] == '}') \
                    or (stop_scan_type == 8 and content[i-1] == "%") \
                    or (stop_scan_type == 9 and content[i-2] == "." and content[i-3] == "%") \
                    or (stop_scan_type == 10 and content[i-1] == "\\" and content[i] == 'n'):
                stop_scan_type = None
            continue
        temp += content[i]
    if temp != "":
        clusters_unit.append(ClusterUnit(temp.strip(), None))
    return clusters_unit


def break_blocks(current_location: CurrentLocation):
    if current_location.offset == -1:
        return None
    current_location.index += 1
    with open("{}\\{}".format(MERGED_FILE_FOLDER, MERGED_RPY_FILE), "r", encoding="utf8") as f:
        f.seek(current_location.offset)
        temp_str = ""
        line_units = []
        is_source_line = True
        while True:
            line = f.readline()
            if not line:
                break
            temp_str += line
            if count_substring_in_string('"', line) > 0:
                if is_source_line:
                    content = get_content_from_raw(line)
                    line_units.append(
                        LineUnit(line, content, break_clusters(content)))
                else:
                    if len(temp_str + line) > MAX_CHAR_IN_THREAD:
                        current_location.offset = f.tell()
                        return BlockUnit(current_location.index, temp_str, line_units)
                is_source_line = not is_source_line
    current_location.offset = -1
    return BlockUnit(current_location.index, temp_str, line_units)


def translate(txt, input_text_area, wait):
    if len(txt) <= 1:
        return txt
    result = ""
    input_text_area.send_keys(txt)
    try:
        # wait text availible
        result = wait.until(
            EC.element_to_be_clickable(
                (By.XPATH, "/html/body/div[2]/div[2]/div[1]/div[2]/div[1]/div[1]/div[2]/div[3]/div[1]/div[2]/div/span[1]"))
        ).text
    except:
        # try something stupid :)))
        input_text_area.send_keys(".")
        try:
            result = wait.until(
                EC.element_to_be_clickable(
                    (By.XPATH, "/html/body/div[2]/div[2]/div[1]/div[2]/div[1]/div[1]/div[2]/div[3]/div[1]/div[2]/div/span[1]"))
            ).text
        except:
            print("Error: Cannot translate")
    try:
        buttonDelte = wait.until(
            EC.element_to_be_clickable(
                (By.XPATH, "/html/body/div[2]/div[2]/div[1]/div[2]/div[1]/div[1]/div[1]/div[2]/div/div/div[2]/div/div"))
        ).click()
    except:
        print("Error: Cannot clear text field")
    return result.replace("<span title class>", "").replace("</span>", "").replace('"', "'")


def process_line(line_unit: LineUnit):
    for cluster in line_unit.clusters_unit:
        line_unit.translated_text = line_unit.translated_text.replace(
            cluster.before_translate, cluster.after_translate)


def process_block(block_unit: BlockUnit, input_text_area, wait, thread_index):
    global total_cluster_translate
    old_before_translate = ""
    old_after_translate = ""
    for line in block_unit.lines_unit:
        for cluster in line.clusters_unit:
            if cluster.before_translate == old_before_translate:
                cluster.after_translate = old_after_translate
                continue
            else:
                cluster.after_translate = translate(
                    cluster.before_translate, input_text_area, wait)
                old_after_translate = cluster.after_translate
            old_before_translate = cluster.before_translate
            total_cluster_translate[thread_index] += 1
    for line in block_unit.lines_unit:
        process_line(line)


def write_block_unit(block_unit: BlockUnit, thread_index):
    global dialogue_thread_done
    index = 0
    with open("{}\\{}".format(BLOCK_TRANSLATED_FOLDER, block_unit.index), "w", encoding="utf-8") as trans_temp:
        is_source_line = True
        buf = io.StringIO(block_unit.raw_text)
        for line in buf:
            if count_substring_in_string('"', line) > 0:
                if not is_source_line:
                    line = line.replace('""', '"{}"'.format(
                        block_unit.lines_unit[index].translated_text))
                    index += 1
                    dialogue_thread_done[thread_index] += 1
                is_source_line = not is_source_line
            trans_temp.write(line)


def count_file_in_folder(directory_path):
    count = 0
    for f in os.listdir(directory_path):
        full_path = os.path.join(directory_path, f)
        if os.path.isfile(full_path):
            count += 1
    return count


def merge_translated_blocks():
    print("--")
    print("Merge the translated blocks...")
    total_temp_file = count_file_in_folder(BLOCK_TRANSLATED_FOLDER)
    with open("{}\\{}".format(MERGED_FILE_FOLDER, MERGED_BLOCK_FILE), "w", encoding="utf-8") as output_file:
        for i in range(total_temp_file):
            with open("{}\\{}".format(BLOCK_TRANSLATED_FOLDER, i+1), "r", encoding="utf8") as f:
                for line in f:
                    output_file.write(line)
    print("-------------Merge completed-------------")


def runner(thread_index, input_lang, output_lang):
    global current_location
    with webdriver.Chrome(executable_path=DRIVER_PATH, options=WEB_DRIVER_OPTIONS) as driver:
        driver.get("https://translate.google.com/?hl=" +
                   input_lang + "#" + input_lang + "/" + output_lang+"/")
        input_text_area = driver.find_element_by_id("source")
        wait = WebDriverWait(driver, MAX_TIME_WAIT_ELEMENT)
        while True:
            block_unit = None
            with lock:
                block_unit = break_blocks(current_location)
            if block_unit is None:
                break
            process_block(block_unit, input_text_area, wait, thread_index)
            write_block_unit(block_unit, thread_index)
            if current_location.offset == -1:
                break


def monitoring_process(total_dialogue):
    global dialogue_thread_done
    global total_cluster_translate
    while True:
        clear_console()
        total = sum(dialogue_thread_done)
        print("Total dialogue: {}".format(int(total_dialogue)))
        print("Process: {}/{}".format(total, int(total_dialogue)))
        print("-----------------------------------------")
        for i in range(len(total_cluster_translate)):
            print("Total translated on thread {}: {}".format(
                i + 1, total_cluster_translate[i]))
        print("-----------------------------------------")
        for i in range(len(dialogue_thread_done)):
            print("Total dialogue done on thread {}: {}".format(
                i + 1, dialogue_thread_done[i]))
        time.sleep(1)
        if total == total_dialogue:
            print("----------Translation completed----------")
            break


def count_string_have_char(char, sourceFile):
    count = 0
    with open(sourceFile, "r", encoding="utf-8") as f:
        for line in f:
            if count_substring_in_string(char, line) > 0:
                count += 1
    return count


def delete_temp_folder():
    if os.path.exists(MERGED_FILE_FOLDER):
        shutil.rmtree(MERGED_FILE_FOLDER, ignore_errors=True)
    if os.path.exists(BLOCK_TRANSLATED_FOLDER):
        shutil.rmtree(BLOCK_TRANSLATED_FOLDER, ignore_errors=True)


def create_temp_folder():
    if not os.path.exists(MERGED_FILE_FOLDER):
        os.mkdir(MERGED_FILE_FOLDER)
    if not os.path.exists(BLOCK_TRANSLATED_FOLDER):
        os.mkdir(BLOCK_TRANSLATED_FOLDER)


def build_rpy_file():
    print("--")
    print("Building rpy file...")
    current_rpy_file_path = ""
    with open("{}\\{}".format(MERGED_FILE_FOLDER, MERGED_BLOCK_FILE), "r", encoding="utf-8") as f:
        while True:
            line = f.readline()
            if not line:
                break
            if count_substring_in_string(SIGN_BREAK_FILE, line) == 2:
                current_rpy_file_path = re.search(
                    "{}(.*){}".format(SIGN_BREAK_FILE, SIGN_BREAK_FILE), line).group(1)
                with open(current_rpy_file_path, "w", encoding="utf-8") as rpy_filefile:
                    while True:
                        line = f.readline()
                        if not line or count_substring_in_string(SIGN_BREAK_FILE, line) == 1:
                            break
                        rpy_filefile.write(line)
    print("-------Rpy file building completed-------")


def main(number_of_thread, input_dỉrectory, input_lang, output_lang):
    start = time.time()
    global current_location
    global dialogue_thread_done
    global total_cluster_translate
    delete_temp_folder()
    create_temp_folder()
    current_location = CurrentLocation(0, 0)
    merge_files(get_rpy_files_in_directory(input_dỉrectory))

    total_dialogue = count_string_have_char(
        '"', "{}\\{}".format(MERGED_FILE_FOLDER, MERGED_RPY_FILE)) / 2

    threads = []
    for i in range(number_of_thread):
        threads.append(threading.Thread(
            target=runner, args=(i, input_lang, output_lang)))
        dialogue_thread_done.append(0)
        total_cluster_translate.append(0)
        threads[i].start()

    monitoring_process(total_dialogue)
    merge_translated_blocks()
    build_rpy_file()
    delete_temp_folder()
    end = time.time()
    print("--")
    print("All done at: {}".format(datetime.now().strftime("%Y/%m/%d %H:%M:%S")))
    print("Total time: {}".format(time.strftime(
        '%H:%M:%S', time.gmtime(end - start))))


def cli():
    print("-------------Translate RenPy-------------")
    input_dỉrectory = input(
        "Enter the directory path containing the .rpy file: ")
    if not is_directory_exists(input_dỉrectory):
        print("Error: The directory does not exist")
        return False
    print("---Enter input and output language code (https://cloud.google.com/translate/docs/languages)---")
    input_lang = input("Input language: ")
    if not input_lang in LANGUAGE_SUPPORT:
        print("Error: '{}' is not a supported language".format(input_lang))
        return False
    output_lang = input("Output language: ")
    if not output_lang in LANGUAGE_SUPPORT:
        print("Error: '{}' is not a supported language".format(output_lang))
        return False
    print("--")
    number_of_thread = input("Enter number of thread: ")
    if number_of_thread == "":
        print("Error: Please enter number of thread")
        return False
    if int(number_of_thread) > 8:
        is_continue = input(
            "Many threads will take high CPU, Do you want continue? (y/n): ")
        if is_continue == "n":
            return False
    print("--")
    show_browser_windows = input(
        "Do you want show browser windows? (y/n): ")
    if show_browser_windows == "y":
        is_continue = input(
            "Show browser windows can take high RAM, do you want continue? (y/n): ")
        if is_continue != "y":
            WEB_DRIVER_OPTIONS.add_argument("--headless")
    else:
        WEB_DRIVER_OPTIONS.add_argument("--headless")
    main(int(number_of_thread), input_dỉrectory, input_lang, output_lang)
    return True


while True:
    clear_console()
    if cli():
        print("--")
        input("Press enter to exist...")
        break