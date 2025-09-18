import requests
from lxml import etree
import os
import json
import re
import time
from login import Login

currClass = 0
session = None
course_dict = {}


def login(username, password):
    """登录并保存 cookies"""
    global session
    session = requests.session()
    cookies_file = os.path.join(os.path.dirname(os.path.realpath(__file__)), "cookies.json")

    if os.path.exists(cookies_file):
        with open(cookies_file, "r") as f:
            session.cookies.update(json.load(f))
            print("cookies存在，使用cookies")
            return

    url = 'http://passport2.chaoxing.com/fanyalogin'
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:91.0) Gecko/20100101 Firefox/91.0',
        'Referer': 'http://passport2.chaoxing.com/login?fid=&newversion=true&refer=http%3A%2F%2Fi.chaoxing.com'
    }
    my_login = Login(username, password)
    my_login.get_information()
    data = {
        'fid': -1,
        'uname': my_login.username,
        'password': my_login.password,
        'refer': 'http%253A%252F%252Fi.chaoxing.com',
        't': True,
        'forbidotherlogin': 0
    }

    res = session.post(url, headers=headers, data=data)
    with open(cookies_file, "w") as f:
        json.dump(res.cookies.get_dict(), f)
    print("登录成功，已保存cookies")


def get_classes():
    """获取课程列表"""
    url = 'http://mooc1-2.chaoxing.com/visit/courses'
    headers = {'User-Agent': 'Mozilla/5.0', 'Referer': 'http://i.chaoxing.com/'}
    res = session.get(url, headers=headers)

    if res.status_code != 200:
        print("error: 课程处理失败")
        return

    class_HTML = etree.HTML(res.text)
    course_dict.clear()
    for i, class_item in enumerate(class_HTML.xpath("/html/body/div/div[2]/div[3]/ul/li[@class='courseItem curFile']"), 1):
        try:
            class_name = class_item.xpath("./div[2]/h3/a/@title")[0]
            class_url = "https://mooc1-2.chaoxing.com{}".format(class_item.xpath("./div[1]/a[1]/@href")[0])
            course_dict[i] = [class_name, class_url]
        except Exception as e:
            print("课程解析异常:", e)


def qiandao(url: str, address: str, sleepTime: int, SENDKEY: str):
    """签到函数"""
    courseid = re.findall(r"courseid=(.*?)&", url)[0]
    clazzid = re.findall(r"clazzid=(.*?)&", url)[0]
    url = f'https://mobilelearn.chaoxing.com/widget/pcpick/stu/index?courseId={courseid}&jclassId={clazzid}'

    headers = {'User-Agent': 'Mozilla/5.0'}
    res = session.get(url, headers=headers)
    tree = etree.HTML(res.text)
    activeDetail = tree.xpath('/html/body/div[2]/div[2]/div/div/div/@onclick')

    if not activeDetail:
        print(course_dict[currClass][0], "------暂无签到活动")
        return

    print('\n', course_dict[currClass][0], "------检测到", len(activeDetail), "个活动。")
    time.sleep(sleepTime)

    for activeID in activeDetail:
        id = re.findall(r'activeDetail\((.*?),', activeID)[0]
        data = session.get(f'https://mobilelearn.chaoxing.com/v2/apis/sign/refreshQRCode?activeId={id}').json().get('data')
        enc = data['enc'] if data else ''
        sign_url = (
            f'https://mobilelearn.chaoxing.com/pptSign/stuSignajax?activeId={id}&clientip=&latitude=-1&longitude=-1'
            f'&appType=15&fid=0&enc={enc}&address={address}'
        )
        res = session.get(sign_url, headers=headers)
        print('**********')
        print(res.text)
        push_serverchan(SENDKEY, res)


def push_serverchan(SENDKEY, res):
    """Server酱推送"""
    if not SENDKEY:
        print("SENDKEY 为空，跳过 server 酱推送")
        return

    if res.text == 'success':
        title = "学习通-签到成功"
        desp = course_dict[currClass][0] + "签到成功"
    elif res.text == '您已签到过了':
        title = "学习通-已签到过了"
        desp = course_dict[currClass][0] + "您已签到过了"
    else:
        title = "学习通-签到失败"
        desp = "签到失败，原因：" + res.text

    r = requests.post(f'https://sctapi.ftqq.com/{SENDKEY}.send', data={'text': title, 'desp': desp})
    if r.status_code == 200:
        print("Server酱推送成功")
    else:
        print("Server酱推送失败", r.status_code)


if __name__ == '__main__':
    username = os.environ["USERNAME"]
    password = os.environ["PASSWORD"]
    SENDKEY = os.environ.get("SENDKEY", "")
    address = os.environ["ADDRESS"]
    sleepTime = 10

    while True:
        login(username, password)
        get_classes()
        if course_dict:
            break
        print("cookie过期，重新登录")
        cookies_file = os.path.join(os.path.dirname(os.path.realpath(__file__)), "cookies.json")
        if os.path.exists(cookies_file):
            os.remove(cookies_file)

    for currClass in course_dict:
        qiandao(course_dict[currClass][1], address, sleepTime, SENDKEY)
