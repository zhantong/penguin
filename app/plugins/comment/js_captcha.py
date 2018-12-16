import time
import random
import hashlib
import json


# from https://strcpy.me/index.php/archives/438/

def split_str(string):
    result = []
    length = len(string)
    start = 0
    while True:
        r = random.randint(0, 3)
        if start + r < length:
            result.append(string[start:start + r])
            start += r
        else:
            result.append(string[start:])
            break
    return result


def rand_str(length=32):
    string = hashlib.md5((str(time.time()) + str(random.randrange(1, 9999999900))).encode()).hexdigest()
    return string[0:length]


def confuse_string():
    s = rand_str()
    str_list = split_str(s)
    str_len = len(s)
    js_var1 = "v" + rand_str(3)
    js_string = "function js_captcha_check(){var " + js_var1 + " = "
    for item in str_list:
        js_string += ("'" + item + "'+" + random.randint(0, 2) * ' ')
        r = random.randint(0, 3)
        if r:
            js_string += ("//" + random.randint(0, 1) * "/*" + rand_str(random.randint(1, 5)) + random.randint(0, 1) * "*/" + "\n")
        else:
            js_string += ("/*" + "/" * random.randint(0, 2) + rand_str(random.randint(2, 4)) + "*/")
    js_var2 = "l" + rand_str(3)
    js_string += ("'';var " + js_var2 + " = ")
    l = []
    result = ""
    for i in range(random.randint(10, 25)):
        l.append(random.randint(0, str_len))
    js_string += (json.dumps(l) + ";" + "\n")
    js_var3 = ("r" + rand_str(3))
    js_string += ("for(var i = 0;i < " + js_var2 + ".length;i++){var " + js_var3 + "= ")
    for i in range(0, len(l)):
        if random.randint(0, 1):
            result += s[0:l[i]]
            js_string += (js_var1 + "." + "/*" + random.randint(0, 2) * "/" + rand_str(random.randint(3, 5)) + "*/" + "substr(0, " + str(l[i]) + ") +" + random.randint(0, 2) * " ")
        else:
            r = random.randint(-100, 30)
            result += str(l[i] + r)
            js_string += ("'" + str(l[i] + r) + "' +" + random.randint(0, 3) * " ")
        if random.randint(0, 1):
            js_string += "\n"
    js_string += ("'';}return " + js_var3 + ";}")
    return js_string, result
