import os
from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

# 配置数据库连接
app.config['SECRET_KEY'] = os.urandom(16)
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+mysqlconnector://root:xz2020@top@10.18.101.200:3306/huiyan'
app.config['UPLOAD_FOLDER'] = 'pic_data'

# 初始化数据库
db = SQLAlchemy(app)

# 定义资料包数据模型
class MaterialPackage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer)
    title = db.Column(db.String(255))
    subject = db.Column(db.Enum('语文', '数学', '英语', '其他'))
    category = db.Column(db.Enum('试卷', '错题', 'pdf'))
    create_time = db.Column(db.TIMESTAMP, server_default=db.func.now())

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'title': self.title,
            'subject': self.subject,
            'category': self.category,
            'create_time': self.create_time
        }

# 定义获取用户资料包数据的路由
@app.route('/api/count', methods=['GET'])
def get_user_material_packages():
    # 获取请求中的用户ID
    user_id = request.args.get('user_id')

    try:
        # 根据用户ID从数据库中查询资料包数据
        material_packages = MaterialPackage.query.filter_by(user_id=user_id).all()
        return jsonify([material_package.to_dict() for material_package in material_packages])
    except Exception as e:
        # 发生异常时返回空列表
        print("Error:", e)
        return jsonify([])

if __name__ == '__main__':
    app.run(debug=True)
