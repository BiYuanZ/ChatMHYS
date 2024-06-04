from docx import Document
import io
import sys
import openai
import re
import requests
import json

def load_gua_ci(file_path):
    document = Document(file_path)
    gua_ci_dict = {}
    for para in document.paragraphs:
        line = para.text.strip()
        if line:
            parts = line.split('\t')
            number_name, yin_yang = parts
            gua_ci_dict[yin_yang.strip()] = number_name.strip()
    return gua_ci_dict

def get_trigram_map():
    return {
        1: "111",
        2: "011",
        3: "101",
        4: "001",
        5: "110",
        6: "010",
        7: "100",
        0: "000"
    }

def get_wuxing_map():
    return {
        "111":"乾金",
        "011":"兑金",
        "101":"离火",
        "001":"震木",
        "110":"巽木",
        "010":"坎水",
        "100":"艮土",
        "000":"坤土"
    }


def get_wuxing_result(ti_gua_wuxing, other_gua_wuxing):
    wuxing_relation = {
        "金": {"生": "水", "克": "木"},
        "水": {"生": "木", "克": "火"},
        "木": {"生": "火", "克": "土"},
        "火": {"生": "土", "克": "金"},
        "土": {"生": "金", "克": "水"}
    }
    if ti_gua_wuxing == other_gua_wuxing:
        return "中吉"
    elif wuxing_relation[other_gua_wuxing]["生"] == ti_gua_wuxing:
        return "大吉"
    elif wuxing_relation[ti_gua_wuxing]["克"] == other_gua_wuxing:
        return "小吉"
    elif wuxing_relation[ti_gua_wuxing]["生"] == other_gua_wuxing:
        return "小凶"
    else:
        return "大凶"

def extract_chinese(text):
    chinese_chars = re.findall(r'[\u4e00-\u9fff]+', text)
    return ''.join(chinese_chars)

def print_wuxing(ti_gua_wuxing, yong_gua_wuxing, shang_hu_gua_wuxing, xia_hu_gua_wuxing, xiao_bian_gua_wuxing):
    print("体卦",ti_gua_wuxing)
    print("用卦", yong_gua_wuxing)
    print("体卦与用卦", get_wuxing_result(ti_gua_wuxing[1:], yong_gua_wuxing[1:]))
    print("上互卦", shang_hu_gua_wuxing)
    print("体卦与上互卦", get_wuxing_result(ti_gua_wuxing[1:], shang_hu_gua_wuxing[1:]))
    print("下互卦", xia_hu_gua_wuxing)
    print("体卦与下互卦", get_wuxing_result(ti_gua_wuxing[1:], xia_hu_gua_wuxing[1:]))
    print("小变卦", xiao_bian_gua_wuxing)
    print("体卦与小变卦", get_wuxing_result(ti_gua_wuxing[1:], xiao_bian_gua_wuxing[1:]))

def to_yin_yang(binary_string):
    return ''.join(['阳爻' if bit == '1' else '阴爻' for bit in binary_string])

def print_gua(gua_yin_yang):
    lines = {
        '阳爻': '-- -- --\n',
        '阴爻': '--    --\n'
    }
    yin_yang_list = [gua_yin_yang[i:i+2] for i in range(0, len(gua_yin_yang), 2)]
    for yin_yang in yin_yang_list:
        print(lines.get(yin_yang, f'Unknown yin yang symbol: {yin_yang}'))

def generate_result(number, gua_ci_dict):
    trigram_map = get_trigram_map()
    hundreds, tens, units = int(number / 100), int((number % 100) / 10), number % 10

    ben_gua = trigram_map[hundreds % 8] + trigram_map[tens % 8]
    ben_gua_yin_yang = to_yin_yang(ben_gua)
    hu_gua = ben_gua[1:4] + ben_gua[2:5]
    hu_gua_yin_yang = to_yin_yang(hu_gua)

    change_position = 6 - (units % 6) if units != 6 else 0
    list_ben_gua = list(ben_gua)
    list_ben_gua[change_position] = '1' if list_ben_gua[change_position] == '0' else '0'
    bian_gua = ''.join(list_ben_gua)
    bian_gua_yin_yang = to_yin_yang(bian_gua)

    a = gua_ci_dict.get(ben_gua_yin_yang, "未知")
    b = gua_ci_dict.get(hu_gua_yin_yang, "未知")
    c = gua_ci_dict.get(bian_gua_yin_yang, "未知")

    wuxing_map = get_wuxing_map()
    ti_gua = ben_gua[:3]
    ti_gua_yin_yang = to_yin_yang(ti_gua)
    ti_gua_wuxing = wuxing_map[ti_gua]

    yong_gua = ben_gua[3:]
    yong_gua_yin_yang = to_yin_yang(yong_gua)
    yong_gua_wuxing = wuxing_map[yong_gua]

    shang_hu_gua = hu_gua[:3]
    shang_hu_gua_yin_yang = to_yin_yang(shang_hu_gua)
    shang_hu_gua_wuxing = wuxing_map[shang_hu_gua]

    xia_hu_gua = hu_gua[3:]
    xia_hu_gua_yin_yang = to_yin_yang(xia_hu_gua)
    xia_hu_gua_wuxing = wuxing_map[xia_hu_gua]

    xiao_bian_gua = bian_gua[:3]
    xiao_bian_gua_yin_yang = to_yin_yang(xiao_bian_gua)
    xiao_bian_gua_wuxing = wuxing_map[xiao_bian_gua]

    return a,b,c,ben_gua_yin_yang,hu_gua_yin_yang,bian_gua_yin_yang,ti_gua_wuxing, yong_gua_wuxing, shang_hu_gua_wuxing, xia_hu_gua_wuxing, xiao_bian_gua_wuxing

def query_knowledge_base(questions, knowledge):
    # 将输入的知识文本按行分割
    lines = knowledge.split('\n')
    # 初始化输出结果
    results = []

    for line in lines:
        # 检查当前行是否以任何一个查询的卦名称开头
        if any(line.startswith(question) for question in questions):
            # 直接将匹配到的行添加到结果中
            results.append(line)

    # 如果没有找到任何匹配的信息，返回一个提示信息
    if not results:
        return "No relevant information found."
    else:
        # 返回所有匹配到的行
        return '\n'.join(results)

gua_ci_dict = load_gua_ci("卦象名称.docx")

output = io.StringIO()
sys.stdout = output

#print("你好，我是chatMHYS，用于梅花易数的算卦解卦。如果你想体验，请心里默念你的问题并给我一个三位数，并告诉我你想到的三位数字和问题。注意请先输入三位数并回车，再输入你提问的问题")

number = int(input(""))
question = input("")
print(question)
a, b, c, ben_gua_yin_yang, hu_gua_yin_yang, bian_gua_yin_yang, ti_gua_wuxing, yong_gua_wuxing, shang_hu_gua_wuxing, xia_hu_gua_wuxing, xiao_bian_gua_wuxing= generate_result(number, gua_ci_dict)

print("本卦", a)
print_gua(ben_gua_yin_yang)
print("\n互卦", b)
print_gua(hu_gua_yin_yang)
print("\n变卦", c)
print_gua(bian_gua_yin_yang)

print_wuxing(ti_gua_wuxing, yong_gua_wuxing, shang_hu_gua_wuxing, xia_hu_gua_wuxing, xiao_bian_gua_wuxing)


sys.stdout = sys.__stdout__
result = output.getvalue()
result = extract_chinese(result)

with open('prompt.txt', 'r', encoding='utf-8') as file:
    lines = file.readlines()

# 修改包含特定标记的行
new_lines = []
for line in lines:
    if "-" in line:
        new_line = line.strip() + result + '\n'
        new_lines.append(new_line)
    else:
        new_lines.append(line)





# 从文件读取知识库内容
with open('KG.txt', 'r', encoding='utf-8') as kg_file:
    knowledge_content = kg_file.read()




knowledge_response = query_knowledge_base([a,b,c], knowledge_content)

# 构建完整的提示
full_prompt = f"{new_lines}\nInformation: {knowledge_response}\nQuestion: {question}"



# 设置请求的 URL 和 API 密钥
url = "https://api.gpts.vin/v1/chat/completions/"
api_key = "sk-I85ZMcmGVYtAoU9ZC354F772B92e4cDbBaFbEe8134BdE415"
# sk-I85ZMcmGVYtAoU9ZC354F772B92e4cDbBaFbEe8134BdE415

headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json"
}

data = {
    "model": "gpt-4-32k",
    "messages": [
        {
            "role": "user",
            "content": full_prompt
        }
    ],
    "max_tokens": 8000,
    "temperature": 0.5,
}

response = requests.post(url, headers=headers, json=data)


response_data = json.loads(response.text)
message_content = response_data["choices"][0]["message"]["content"]
with open("output.txt", "w", encoding="utf-8") as file:
    file.write(message_content)

print("本卦", a)
print_gua(ben_gua_yin_yang)
print("\n互卦", b)
print_gua(hu_gua_yin_yang)
print("\n变卦", c)
print_gua(bian_gua_yin_yang)

print_wuxing(ti_gua_wuxing, yong_gua_wuxing, shang_hu_gua_wuxing, xia_hu_gua_wuxing, xiao_bian_gua_wuxing)

print(message_content)