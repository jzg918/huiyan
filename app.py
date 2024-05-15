import os
import time
import requests
import base64
import logging
from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory

from flask_sqlalchemy import SQLAlchemy

from functools import lru_cache

# 日志配置
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# 从环境变量读取敏感信息
# API_KEY = os.getenv('BAIDU_API_KEY')
# SECRET_KEY = os.getenv('BAIDU_SECRET_KEY')
# if not API_KEY or not SECRET_KEY:
#     logging.error("API_KEY 或 SECRET_KEY 未设置。")
#     exit(1)
API_KEY = "rILk4PARJt77WG2BsZ5J57pg"
SECRET_KEY = "y81gJhuMrWWMIznMo3VPAy9crycNFveO"

app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(16)
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+mysqlconnector://root:root@localhost:8889/huiyan'
app.config['UPLOAD_FOLDER'] = 'pic_data'

db = SQLAlchemy(app)

@app.route('/health', methods=['GET'])
def app_health():
    return "<h1>Welcome 老罗!</h1>"

@app.route('/', methods=['GET'])
def upload_form():
    page = request.args.get('page', 1, type=int)
    upload_form = PicList.query.order_by(PicList.id.desc()).paginate(page=page, per_page=10)

    if not upload_form.items:
        flash("目前没有图片，欢迎上传！", category='info')

    return render_template('upload_form.html', upload_form=upload_form)

class PicList(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    pic_url = db.Column(db.String(200), nullable=False)

# 获取百度API的Access Token，使用lru_cache进行缓存
@lru_cache(maxsize=1)
def get_access_token():
    url = "https://aip.baidubce.com/oauth/2.0/token"
    params = {"grant_type": "client_credentials", "client_id": API_KEY, "client_secret": SECRET_KEY}
    response = requests.post(url, params=params)
    access_token = response.json().get("access_token")
    return access_token

# 将文件转换成Base64编码
def file_to_base64(file_path):
    try:
        with open(file_path, "rb") as f:
            base64_data = base64.b64encode(f.read()).decode("utf-8")
        return base64_data
    except FileNotFoundError:
        logging.error(f"文件未找到: {file_path}")
        return None
    except Exception as e:
        logging.error(f"读取文件时发生错误: {e}")
        return None

# 调用百度API处理图片
def process_image(base64_data):
    url = f"https://aip.baidubce.com/rest/2.0/ocr/v1/remove_handwriting?access_token={get_access_token()}"
    payload = {'image': base64_data}
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}

    try:
        response = requests.post(url, headers=headers, data=payload)
        logging.debug(f"API响应状态码：{response.status_code}")

        if response.status_code == 200:
            result = response.json()
            logging.debug(f"API返回的JSON数据：{result}")

            if "error_code" in result:
                logging.error(f"API返回错误，错误码：{result['error_code']}, 错误信息：{result.get('error_msg')}")
                return None
            else:
                enhanced_image_base64 = result.get("image_processed")
                if enhanced_image_base64:
                    # 保存图片
                    save_image_from_base64(enhanced_image_base64, 'enhanced_image.jpg')
                return enhanced_image_base64
        else:
            logging.error(f"API请求失败，状态码：{response.status_code}")
            return None
    except Exception as e:
        logging.error(f"调用百度API时出现异常: {e}")
        return None


# 保存Base64编码为图像文件
def save_image_from_base64(base64_data, file_path):
    with open(file_path, "wb") as f:
        f.write(base64.b64decode(base64_data))

@app.route('/upload', methods=['POST'])
def upload():
    name = request.form.get('name')
    file = request.files.get('pic')

    if not name or not file:
        flash("请确保提供了图片名称和文件。", 'error')
        return redirect(url_for('upload_form'))

    # 获取上传文件的扩展名，并将其转换为小写形式。
    uploaded_file_extension = os.path.splitext(file.filename)[1].lower()
    # 定义了支持的图片文件扩展名的集合
    supported_extensions = {'.jpg', '.jpeg', '.png', '.gif'}

    # 检查上传的文件扩展名是否在支持的扩展名集合中。如果不在集合中，则会闪现一条错误消息，并重定向到上传表单页面
    if uploaded_file_extension not in supported_extensions:
        flash("上传失败：只支持.jpg, .jpeg, .png, .gif格式的图片，请重新选择。", 'error')
        return redirect(url_for('upload_form'))

    try:
        # 获取当前时间戳
        timestamp = int(time.time())

        # 生成一个唯一的ID，并将其填充为3位数的字符串
        last_pic = PicList.query.order_by(PicList.id.desc()).first()

        # 获取最后一个图片的ID，并将其填充为3位数的字符串
        last_id = last_pic.id if last_pic else 0

        # 获取最后一个图片的ID，并将其填充为3位数的字符串
        pic_id = str(last_id + 1).zfill(3)

        # 构建原始图片文件的文件名，包含时间戳、图片 ID 和文件扩展名
        original_filename = f"{timestamp}_{pic_id}{os.path.splitext(file.filename)[1]}"

        # 将上传的文件保存到服务器上的指定文件夹中
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], original_filename))

        # 保存的图片文件转换为 Base64 编码数据
        base64_data = file_to_base64(os.path.join(app.config['UPLOAD_FOLDER'], original_filename))

        # 调用百度API处理图片 Base64 编码数据
        enhanced_base64_data = process_image(base64_data)
        logging.debug(f"增强后的图片数据：{enhanced_base64_data}")
        print(enhanced_base64_data)

        # 如果增强后的图像数据不为空，则保存增强后的图像文件
        if enhanced_base64_data is not None:
            # 构建增强后的图片文件名
            enhanced_filename = f"{os.path.splitext(original_filename)[0]}_enhanced{os.path.splitext(original_filename)[1]}"
            # 保存增强后的图像文件
            save_image_from_base64(enhanced_base64_data, os.path.join(app.config['UPLOAD_FOLDER'], enhanced_filename))

            new_pic = PicList(name=name, pic_url=os.path.join('pic_data', enhanced_filename))
            db.session.add(new_pic)
            db.session.commit()

            flash("图片上传成功。", 'success')
        else:
            flash("处理图片时出现问题，上传失败。", 'error')
    except Exception as e:
        logging.error(f"上传过程中发生错误: {e}")
        flash("上传过程中发生错误，请稍后重试。", 'error')

    return redirect(url_for('upload_form'))

@app.route('/pic_data/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

if __name__ == '__main__':
    app.run(debug=True)
