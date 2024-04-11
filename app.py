from flask import Flask, render_template, redirect, url_for, session, request, jsonify, flash,session, json
from flask_cors import CORS
from pymongo import MongoClient
from bson.objectid import ObjectId
from bson import json_util, ObjectId
from datetime import timedelta, timezone, datetime
import os
import pyotp
import qrcode
import hashlib
import json
import random
from flask_apscheduler import APScheduler 
import requests
import qrcode
import pytz
from werkzeug.utils import secure_filename
from io import BytesIO
import base64
import uuid
from flask import Response
from datetime import datetime
import traceback  # 引入 traceback 模块
from apscheduler.schedulers.blocking import BlockingScheduler



scheduler = BlockingScheduler()

# 使用pytz指定UTC时区
scheduler = BlockingScheduler()
utc_zone = pytz.timezone('Asia/Taipei')

def job_function():
    print("执行任务")

# 使用add_job方法来安排任务
scheduler.add_job(job_function, 'interval', id='do_job_1', max_instances=100, misfire_grace_time=60, minutes=60, timezone=utc_zone)

scheduler.start()


basedir = os.path.abspath(os.path.dirname(__file__))
UPLOAD_FOLDER = basedir+'\public\image'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        try:
            if isinstance(obj, datetime):
                return obj.isoformat()
            iterable = iter(obj)
        except TypeError:
            pass
        else:
            return list(iterable)
        return json.JSONEncoder.default(self, obj)
app = Flask(
    __name__,
    static_folder='public',
    static_url_path='/'
)  
CORS(app)  # 这将使得整个应用都允许跨域请求

app.json_encoder = CustomJSONEncoder

app.secret_key = os.urandom(24)
app.permanent_session_lifetime = timedelta(minutes=60)
app.config['SECRET_KEY'] = os.urandom(24)


connection_string = 'mongodb+srv://samsonm825:g4zo1j6y94@cluster0.ow4o5g4.mongodb.net/?retryWrites=true&w=majority'
client = MongoClient(connection_string)
dbs = client.bittop

key = 'iLufaMySuperSecretKey'
scheduler = APScheduler()
scheduler.init_app(app)
scheduler.start()

@app.route('/', methods=['GET', 'PSOT'])
def index():
    return render_template('index.html')

@app.route('/admin_manifestOrder', methods=['GET', 'POST'])
def admin_manifestOrder():
  if 'id' in session and session['display_name'] == '最高管理者':
    orderNo_data = []
    page_data = {}
    order_data = []
    match = {}
    match_data = {}

    if request.method == 'POST':
      # 條件判斷
      oId = request.form['no']
      name = request.form['name']
      if oId != '':
        match['orderNo'] = {'$regex': oId}
      if name != '':
        match['name'] = name

    if request.args.get('methods') == 'setorderno':
      oid = request.args.get('oid')
      orderNo = request.args.get('orderno')
      match_no = request.args.get('match_no')
      match_name = request.args.get('match_name')
      if match_no != "":
        match['orderNo'] = {'$regex': match_no}
      if match_name != "":
        match['name'] = match_name
      order_data_temp = dbs.jeg_order.find_one(
        {
          "_id": ObjectId(oid)
        }
      )

      dbs.jeg_order.update_one(
        {
          "_id": ObjectId(oid)
        },
        {
          "$set": {
            "order_detail": ObjectId(orderNo)
          }
        }
      )

      dbs.order_no.update_one(
        {
          "_id": ObjectId(orderNo)
        },
        {
          "$set": {
            "is_used": True
          },
          "$push": {
            "used_oid": order_data_temp['bankAccount']
          }
        }
      )
      if match_no == 'undefined' and match_name == 'undefined':
        return redirect('admin_manifestOrder')

    current_page = request.args.get('page')
    skip = 0
    per = 20
    if current_page != None:
      skip = per * (int(current_page) - 1)
    else:
      current_page = 1

    # 判斷條件時要加入 篩選條件
    order_len = dbs.jeg_order.count_documents(match)
    if order_len % per == 0:
      all_page = order_len // per
    else:
      all_page = (order_len // per) + 1
    page_data['all_page'] = all_page
    page_data['current_page'] = current_page
    #分頁處理結束

    if 'name' in match or 'orderNo' in match:
      skip = 0
      per = 10000
      page_data = {}


    temp_data = dbs.jeg_order.find(match).limit(per).skip(skip)
    for doc in temp_data:
      doc['_id'] = str(doc['_id'])
      doc['uid'] = str(doc['uid'])
      if 'order_detail' not in doc:
        doc['order_detail'] = False
      order_data.append(doc)
    
    if 'orderNo' in match  and 'name' in match:
      match_data = {
        "no": match['orderNo']['$regex'],
        "name": match['name']
      }
    elif 'orderNo' in match and 'name' not in match:
      match_data = {
        "no": match['orderNo']['$regex'],
        "name": ""
      }
    elif 'name' in match and 'orderNo' not in match:
      match_data = {
        "no": "",
        "name": match['name']
      }
    print(match)
    return render_template('admin_manifestOrder.html', order_data=order_data, page_data=page_data, match_data=match_data)
  else:
    return redirect('admin_login')
@app.route('/admin_manifestUser', methods=['GET', 'POST'])
def admin_manifestUser():
    if 'id' in session and session['display_name'] == '最高管理者':
        user_data = []
        if request.method == "POST":
            if request.form['name'] == '' or request.form['account'] == '' or request.form['password'] == '':
                flash('栏位不能有空值 请重新填写后送出')
                return redirect("admin_manifestUser")       
            if request.form['id'] !="":
                dbs.jeg_user.update_one(
                    {
                        "_id":ObjectId(request.form['id'])
                    },
                    {
                        "$set":{
                            "name":request.form['name'],
                            "account":request.form['account'],
                            "password":request.form['password'],
                        }
                    }
                )
            else:
                user = dbs.jeg_user.find_one(
                    {
                        "account":request.form['account'],
                    }
                )
                if user == None:
                    dbs.jeg_user.insert_one(
                    {
                        "name":request.form['name'],
                        "account":request.form['account'],
                        "password":request.form['password'],
                    }                    
                )
                else:
                    flash('账号重复注册 请确认之后重新新增')

            return redirect("admin_manifestUser")  
        else:
            if request.args.get('methods') == 'delete':
                dbs.jeg_user.delete_one(
                    {
                        "_id": ObjectId(request.args.get('id'))
                    }
                )
                return redirect("admin_manifestUser") 
            temp_data = dbs.jeg_user.find()
            for doc in temp_data:
                doc["_id"] = str(doc["_id"])
                user_data.append(doc)

            return render_template('admin_manifestUser.html', user_data=user_data)
    else:
        return redirect('admin_login') 

@scheduler.task('interval', id='do_job_1', max_instances=100, misfire_grace_time=60, minutes=60)
def job1():
    product_data = []
    member_data = []
    product_find = dbs.product.find(
        {
            'is_buy': False
        }
    )
    for doc in product_find:
        product_data.append(doc)

    member_find = dbs.member.find(
        {
            'is_verify': 1,
            'status': True
        }
    )
    for doc in member_find:
        member_data.append(doc)

    random.shuffle(member_data)

    for pindex, product in enumerate(product_data):
        for mindex, member in enumerate(member_data):
            if member['coin'] >= product['price']:
                dbs.order.insert_one({
                    'product_id': ObjectId(product['_id']),
                    'mid': ObjectId(member['_id']),
                    'is_paid': False,
                    'prove_img': '',
                    'status': False,
                    'factory_id': ''
                })

                order_data = dbs.order.find_one({ 'product_id': ObjectId(product['_id'])})
                member_data = dbs.member.find_one({ "_id":ObjectId(member['_id']) })
                product_data = dbs.product.find_one({"_id":ObjectId(product['_id'])})

                payload = {
                    'oId': str(order_data['_id']),
                    'p_name': product_data['name'],
                    'bank_account': member_data['bankAccount']
                }

                res = requests.post('http://127.0.0.1:5001/api/v1/send_order', json=payload)
                res_data = res.json()

                dbs.order.update_one(
                    {
                        '_id': ObjectId(order_data['_id'])
                    },
                    {
                        '$set': {
                            'factory_id': res_data['data']['factory_id']
                        }
                    }
                )
                dbs.member.update_one(
                    {
                        '_id': ObjectId(member['_id'])
                    },
                    {
                        '$set': {
                            'coin': member['coin'] - product['price'],
                            'status': False
                        }
                    }
                )
                dbs.product.update_one(
                    {
                        '_id': ObjectId(product['_id'])
                    },
                    {
                        '$set': {
                            'is_buy': True
                        }
                    }
                )
                member_data.pop(mindex)
# 将资料转换成json存入资料库
# jsonFile = open('example.json','r',encoding='UTF-8')
# jsonF = json.load(jsonFile)
# i = 1
# for doc in jsonF:
#     data = {
#         'name':doc['姓名'],
#         'phone':'0' + str(doc['电话']),
#         'address':doc['地址'].replace('\t', ''),
#         'number':i
#     }
#     i =  i + 1
#     dbs.fake_data.insert_one(data)


def verify_potp(potp):
    totp = pyotp.TOTP(key)
    result = totp.verify(potp)
    return result


def allowed_file(filename):
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def random_number(count):
    number_list = []
    for i in range(999):
        number_list.append(i)
    random.shuffle(number_list)
    return number_list[0:count]


# @app.route('/', methods=['GET', 'POST'])
# def index():
#     if request.method == 'POST':
#         member_data = []
#         account = request.form['account']
#         password = request.form['password']
#         potp = request.form['potp']
#         session['account'] = account

#         pottp_resul = verify_potp(potp)

#         member_find = dbs.bittop_member.find({
#             'account': account
#         })
#         for doc in member_find:
#             member_data.append(doc)
#         if len(member_data) <= 0:
#             return redirect('index')
#         password_str = password + member_data[0]['salt']
#         user_password = hashlib.sha1(password_str.encode('utf-8'))

#         if member_data[0]['password'] == user_password.hexdigest():
#             session.permanent = True
#             session['display_name'] = member_data[0]['display_name']
#             session['id'] = str(member_data[0]['_id'])
#             return redirect('member_dashboard')
#         else:
#             return redirect('index.html')
#     else:
#         if 'display_name' in session:
#             return redirect('member_dashboard')
#         return render_template('index.html')

# @app.route('/', methods=['GET', 'PSOT'])
# def index():
#     return render_template('login.html')

@app.route('/resetPassword', methods=['GET', 'POST'])
def resetPassword():
    if request.method == 'POST':
        account = request.form['account']
        password2 = request.form['password2']  # 用户的密保答案
        new_password = request.form['password']
        repeat_password = request.form['repeatPassword']

        # 查找匹配的账号和密保问题答案
        member_data = dbs.bittop_member.find_one({'account': account, 'password2': password2})

        if member_data:
            if new_password == repeat_password:
                # 密码加盐和哈希处理
                password_str = new_password + member_data['salt']
                user_password = hashlib.sha1(password_str.encode('utf-8'))

                # 更新密码
                dbs.bittop_member.update_one(
                    {
                        '_id': member_data['_id']
                    },
                    {
                        '$set': {
                            'password': user_password.hexdigest()
                        }
                    }
                )
                session.clear()
                return render_template('success2.html')
            else:
                # 新密码和重复密码不匹配
                render_template('resetPassword.html')
        else:
            # 账号或密保问题答案不匹配
            render_template('resetPassword.html')
    else:
        return render_template('resetPassword.html')




@app.route('/admin_usdt', methods=['GET', 'POST'])
def admin_usdt():
    if 'display_name' in session and session['display_name'] == '最高管理者':
        # 合并来自 usdtPlus 和 usdtminus 的数据
        usdtPlus_data = list(dbs.usdtPlus.find({}))
        for data in usdtPlus_data:
            data['type'] = 'plus'
        usdtminus_data = list(dbs.usdtminus.find({}))
        for data in usdtminus_data:
            data['type'] = 'minus'

        usdt_data = usdtPlus_data + usdtminus_data
        usdt_data = sorted(usdt_data, key=lambda x: x['time'], reverse=True)
        search_account = request.args.get('search_account', '').strip()  # 获取搜索参数
        if search_account:  # 如果提供了搜索参数
            # 过滤usdt_data，只保留匹配搜索账号的数据
            usdt_data = [data for data in usdt_data if search_account in data.get('account', '')]

        if request.method == 'GET' and 'method' in request.args and 'bId' in request.args:
            method = request.args.get('method')
            record_id = ObjectId(request.args.get('bId'))
            record = next((item for item in usdt_data if item['_id'] == record_id), None)

            if record:
                member_data = dbs.bittop_member.find_one({'account': record['account']})

                # 检查订单是否已经被处理
                if record.get('status') == True:
                    return jsonify({'message': 'This order has already been processed.'})

                if method == 'success' and record['type'] == 'plus':
                    # 更新用户的 USDT 余额
                    new_usdt_balance = member_data['USDT'] + float(record['usdtcount'])
                    Taipei_tz = pytz.timezone('Asia/Taipei')
                    now_in_taipei = datetime.now(Taipei_tz)
                    local_now = now_in_taipei.replace(tzinfo=None)


                    dbs.bittop_member.update_one({'_id': member_data['_id']}, {'$set': {'USDT': new_usdt_balance, 'mUSDT': new_usdt_balance}})
                    dbs.usdtPlus.update_one({'_id': record_id}, {'$set': {'status': True}})
                    # Log the transaction
                    dbs.member_usdtlog.insert_one({
                        'account': record['account'],
                        'usdtcount': record['usdtcount'],
                        'time': record['time'],
                        'type': '充值',
                        'USDT': new_usdt_balance,
                        'date': local_now,  # 这里存储完整的当前时间（年月日时分秒）
                        'uptime': datetime.now(Taipei_tz).strftime('%Y-%m-%d %H:%M:%S'),
                    })
                elif method == 'cancel' and record['type'] == 'plus':
                    # 确认取消充值订单
                    dbs.usdtPlus.delete_one({'_id': record_id})
                    Taipei_tz = pytz.timezone('Asia/Taipei')
                    now_in_taipei = datetime.now(Taipei_tz)
                    local_now = now_in_taipei.replace(tzinfo=None)

                    # Log the cancellation
                    dbs.member_usdtlog.insert_one({
                        'account': record['account'],
                        'usdtcount': record['usdtcount'],
                        'time': record['time'],
                        'type': '充值失败',
                        'USDT': member_data['USDT'],
                        'date': local_now,  # 这里存储完整的当前时间（年月日时分秒）
                        'uptime': datetime.now(Taipei_tz).strftime('%Y-%m-%d %H:%M:%S'),
                    })
                elif method == 'success' and record['type'] == 'minus':
                    # 更新用户的 USDT 余额
                    new_usdt_balance = member_data['USDT'] - float(record['usdtout'])
                    dbs.bittop_member.update_one({'_id': member_data['_id']}, {'$set': {'USDT': new_usdt_balance}})
                    dbs.usdtminus.update_one({'_id': record_id}, {'$set': {'status': True}})
                    Taipei_tz = pytz.timezone('Asia/Taipei')
                    now_in_taipei = datetime.now(Taipei_tz)
                    local_now = now_in_taipei.replace(tzinfo=None)
                    # Log the transaction
                    dbs.member_usdtlog.insert_one({
                        'account': record['account'],
                        'usdtcount': -float(record['usdtout']),
                        'time': record['time'],
                        'type': '提领',
                        'USDT': new_usdt_balance,
                        'date': local_now,  # 这里存储完整的当前时间（年月日时分秒）
                        'uptime': datetime.now(Taipei_tz).strftime('%Y-%m-%d %H:%M:%S'),
                    })
                elif method == 'cancel' and record['type'] == 'minus':
                    # 确认取消提领订单
                    new_usdt_balance = member_data['mUSDT'] + float(record['usdtout'])
                    dbs.bittop_member.update_one({'_id': member_data['_id']}, {'$set': {'mUSDT': new_usdt_balance}})
                    dbs.usdtminus.delete_one({'_id': record_id})
                    Taipei_tz = pytz.timezone('Asia/Taipei')
                    now_in_taipei = datetime.now(Taipei_tz)
                    local_now = now_in_taipei.replace(tzinfo=None)

                    # Log the cancellation
                    dbs.member_usdtlog.insert_one({
                        'account': record['account'],
                        'usdtcount': record['usdtout'],
                        'time': record['time'],
                        'type': '提领失败',
                        'date': local_now,  # 这里存储完整的当前时间（年月日时分秒）
                        'USDT':  member_data['USDT'],
                        'uptime': datetime.now(Taipei_tz).strftime('%Y-%m-%d %H:%M:%S'),
                    })

                return redirect(url_for('admin_usdt'))

        return render_template('admin_usdt.html', usdt_data=usdt_data)
    else:
        return redirect('admin_login')

@app.route('/check_status', methods=['GET'])
def check_status():
    record_id = ObjectId(request.args.get('bId'))
    record = dbs.usdtPlus.find_one({'_id': record_id}) or dbs.usdtminus.find_one({'_id': record_id})
    if record:
        return jsonify({'status': 'already_processed' if record.get('status') else 'not_processed'})
    return jsonify({'status': 'not_found'})

# @app.route('/admin_usdt', methods=['GET', 'POST'])
# def admin_usdt():
#     if 'display_name' in session and session['display_name'] == '最高管理者':
#         if request.method == 'GET':
#             if request.args.get('method') == 'success':
#                 dbs.usdtPlus.update_one(
#                     {
#                         '_id': ObjectId(request.args.get('bId'))
#                     },
#                     {
#                         '$set':{
#                             'status': True
#                         }
#                     }           
#                 )
#             elif request.args.get('method') == 'falid':
#                 usdt_data = dbs.usdtPlus.find_one({ '_id': ObjectId(request.args.get('bId')) })
#                 member_data = dbs.bittop_member.find_one({ 'account': usdt_data['account'] })
#                 dbs.bittop_member.update_one(
#                     {
#                         '_id': ObjectId(member_data['_id'])
#                     },
#                     {
#                         '$set':{
#                             'USDT': member_data['USDT'] - float(usdt_data['usdtcount'])
#                         }
#                     }
#                 )
#                 dbs.usdtPlus.delete_one({ '_id': ObjectId(request.args.get('bId')) })


#             dvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv
#     elif 'id' in session and request.method == 'POST':
#         member_data = dbs.bittop_member.find_one({'_id': ObjectId(session['id'])})
#         usdt_count = request.form['usdtcount']
#         if float(usdt_count) > member_data['USDT']:
#             return redirect('memberdousdt')
#         else:
#             new_usdt_balance = member_data['USDT'] - float(usdt_count)
#             data = {
#                 'account': member_data['account'],
#                 'USDT': new_usdt_balance,
#                 'usdtcount': float(usdt_count),
#                 'status': False
#             }
#             dbs.usdtPlus.insert_one(data)

#             dbs.bittop_member.update_one(
#                 {'_id': ObjectId(session['id'])},
#                 {'$set': {'USDT': new_usdt_balance}}
#             )
#             return redirect('memberdousdt')


# @app.route('/admin_usdt', methods=['GET', 'POST'])
# def admin_usdt():
#     if 'display_name' in session and session['display_name'] == '最高管理者':
#         if request.method == 'GET':
#             if request.args.get('method') == 'success':
#                 # 获取交易记录
                
#                 usdt_data = dbs.usdtPlus.find_one({ '_id': ObjectId(request.args.get('bId')) })
                

#                 # 更新会员USDT余额
#                 member_data = dbs.bittop_member.find_one({ 'account': usdt_data['account'] })
#                 new_usdt_balance = member_data['USDT'] + float(usdt_data['usdtcount'])
#                 dbs.bittop_member.update_one(
#                     {
#                         '_id': ObjectId(member_data['_id'])
#                     },
#                     {
#                         '$set':{
#                             'USDT': new_usdt_balance
#                         }
#                     }
#                 )

#                 # 更新交易状态为成功
#                 dbs.usdtPlus.update_one(
#                     {
#                         '_id': ObjectId(request.args.get('bId'))
#                     },
#                     {
#                         '$set':{
#                             'status': True
#                         }
#                     }           
#                 )
#             elif request.args.get('method') == 'success':
#                 usdt_data = dbs.usdtPlus.find_one({ '_id': ObjectId(request.args.get('bId')) })
#                 member_data = dbs.bittop_member.find_one({ 'account': usdt_data['account'] })
#                 dbs.bittop_member.update_one(
#                     {
#                         '_id': ObjectId(member_data['_id'])
#                     },
#                     {
#                         '$set':{
#                             'USDT': member_data['USDT'] + float(usdt_data['usdtcount'])
#                         }
#                     }
#                 )
#                 dbs.usdtPlus.delete_one({ '_id': ObjectId(request.args.get('bId')) })


#             usdt_data = []
#             usdt_find = dbs.usdtPlus.find({})
#             for doc in usdt_find:
#                 usdt_data.append(doc)
#             return render_template('admin_usdt.html', usdt_data=usdt_data)
#     elif 'id' in session and request.method == 'POST':
#         member_data = dbs.bittop_member.find_one({ '_id': ObjectId(session['id']) })
#         usdt_count = request.form['USDT']
#         if float(usdt_count) > member_data['USDT']:
#             return redirect('profile')
#         else:
#             data = {
#                 'name': member_data['name'],
#                 'account': member_data['account'],
#                 'USDT': member_data['USDT'] - float(usdt_count),
#                 'usdtcount': float(usdt_count),
#                 'status': False
#             }
#             dbs.usdtPlus.insert_one(data)

#             dbs.bittop_member.update_one(
#                 {
#                     '_id': ObjectId(session['id'])
#                 },
#                 {
#                     '$set':{
#                         'USDT':member_data['USDT'] - float(usdt_count)
#                     }
#                 }
#             )
#             return redirect('admin_usdt')
#     else:
#         return redirect('admin_login')



@app.route('/admin_log', methods=['GET', 'POST'])
def admin_log():
    if 'account' in session:
        # 获取筛选参数
        account_filter = request.args.get('account')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')

        # 构建查询条件
        query = {}
        if account_filter:
            query['account'] = account_filter

        # 格式化日期并添加到查询条件（确保数据库中的日期格式匹配）
        if start_date:
            start_date = datetime.strptime(start_date, '%Y-%m-%d')
            query['date'] = {'$gte': start_date}
        if end_date:
            end_date = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)  # 将结束日期设置为次日凌晨
            query['date'] = query.get('date', {})
            query['date']['$lte'] = end_date

        # 从member_usdtlog集合中获取与当前用户相关的记录，并按时间降序排序
        log_data = list(dbs.member_usdtlog.find(query).sort('date', -1))

        # 将数据整理为前端所需格式
        record_data = []
        for item in log_data:
            record = {
                'account': item.get('account', ''),
                'amount': item.get('usdtcount', 0) if 'usdtcount' in item else item.get('usdtout', 0),
                'USDT': item.get('USDT', 0),
                'tradetype': item.get('type', ''),
                'uptime': item.get('uptime', None),
                'date':item.get('date', None)
            }
            record_data.append(record)

        return render_template('admin_log.html', record_data=record_data)
    else:
        return redirect('login')

@app.route('/member_log', methods=['GET'])
def member_log():
    if 'account' in session:
        user_account = session['account']  # 获取当前登录的用户账号

        # 获取前端传来的日期范围
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')

        # 构建查询条件
        query = {'account': user_account}
        if start_date and end_date:
            # 将字符串转换为日期对象
            start_date = datetime.strptime(start_date, '%Y-%m-%d')
            end_date = datetime.strptime(end_date, '%Y-%m-%d')
            end_date = end_date + timedelta(days=1)  # 包括结束日期当天
            query['date'] = {'$gte': start_date, '$lt': end_date}

        # 查询数据库并按时间降序排序
        log_data = list(dbs.member_usdtlog.find(query).sort('date', -1))

        # 初始化总量变量
        total_withdrawn = 0
        total_deposited = 0
        total_sold = 0

        # 将数据整理为前端所需格式
        record_data = []
        for item in log_data:
            amount = float(item.get('usdtcount', 0)) if 'usdtcount' in item else float(item.get('usdtout', 0))
            tradetype = item.get('type', '')

            # 根据筛选结果计算总量
            if tradetype == '提领':
                total_withdrawn += amount*-1
            elif tradetype == '充值':
                total_deposited += amount
            elif tradetype == '售出':
                total_sold += amount

            record = {
                'account': user_account,
                'amount': amount,
                'USDT': item.get('USDT', 0),
                'tradetype': tradetype,
                'time': item.get('time', None),
                'uptime': item.get('uptime', None)
            }
            record_data.append(record)

        # 传递排序后的数据和总量到前端模板
        return render_template('member_log.html', 
                               record_data=record_data,
                               total_withdrawn=total_withdrawn,
                               total_deposited=total_deposited,
                               total_sold=total_sold)
    else:
        return redirect('login')

def calculate_total(account, tradetype):
    # 根据账户和交易类型计算总量
    pipeline = [
        {"$match": {"account": account, "type": tradetype}},
        {"$group": {"_id": None, "total": {"$sum": "$usdtcount"}}}
    ]
    total = list(dbs.member_usdtlog.aggregate(pipeline))
    return abs(total[0]['total']) if total else 0
# @app.route('/resetPassword', methods=['GET', 'POST'])
# def resetPassword():
#         if request.method == 'POST':
#             old_password = request.form['oldPassword']
#             password = request.form['password']
#             repeat_password = request.form['repeatPassword']
#             member_data = dbs.member.find_one({'_id': ObjectId(session['id'])})
#             old_password_str = old_password + member_data['salt']
#             old_password = hashlib.sha1(old_password_str.encode('utf-8'))

#             if member_data['password'] == old_password.hexdigest() and password == repeat_password:
#                 password_str = password + member_data['salt']
#                 user_password = hashlib.sha1(password_str.encode('utf-8'))
#                 dbs.member.update_one(
#                     {
#                         '_id': ObjectId(session['id'])
#                     },
#                     {
#                         '$set': {
#                             'password': user_password.hexdigest()
#                         }
#                     }
#                 )
#                 session.clear()
#                 return redirect('login')

#             else:
#                 return redirect('resetPassword')
#         else:
#             return redirect('login')
    
def get_all_subordinates(account, all_subs=None):
    if all_subs is None:
        all_subs = []
    # 使用传入的account变量查询数据库
    user_info = dbs.bittop_member.find_one({'account': account})
    print(account)
    print("检查用户信息:", user_info)  # 打印检查用户信息

    if user_info and 'subordinates' in user_info:
        for subordinate in user_info['subordinates']:
            all_subs.append(subordinate)
            get_all_subordinates(subordinate, all_subs)
        print(all_subs)
    return list(set(all_subs))

@app.route('/member_subordinates', methods=['GET'])
def member_subordinates():
    if 'account' in session:
        user_account = session['account']
        all_subordinates = get_all_subordinates(user_account)

        today = datetime.today()
        start_date = request.args.get('start_date') or today.strftime('%Y-%m-%d')
        end_date = request.args.get('end_date') or today.strftime('%Y-%m-%d')
        search_account = request.args.get('search_account', '').strip()


        start_date = datetime.strptime(start_date, '%Y-%m-%d')
        end_date = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)
        if search_account:
            all_subordinates = [account for account in all_subordinates if search_account.lower() in account.lower()]

        account_totals = {account: 0 for account in all_subordinates}  # 初始化为0
        account_usdt = {}  # 存储每个账号的USDT余额

        # 获取每个账号的交易记录并更新account_totals
        for account in all_subordinates:
            query = {'account': account, 'type': '售出', 'date': {'$gte': start_date, '$lt': end_date}}
            sold_records = list(dbs.member_usdtlog.find(query).sort('date', -1))
            for record in sold_records:
                amount = float(record.get('usdtcount', 0))
                account_totals[account] += amount

            # 获取每个账号的USDT余额
            member_data = dbs.bittop_member.find_one({'account': account})
            account_usdt[account] = member_data.get('USDT', 0) if member_data else 0

        return render_template('member_subordinates.html', account_totals=account_totals, account_usdt=account_usdt)
    else:
        return redirect('login')
@app.route('/cart/<product>')
def cart(product):
    if 'id' in session:
        member_data = dbs.member.find_one({'_id': ObjectId(session['id'])})

        if product == 'all':
            product_data = []
            product_find = dbs.product.find(
                {
                    'is_buy': False,
                    'price': {
                        '$lte': member_data['coin']
                    }
                }
            )
            for doc in product_find:
                product_data.append(doc)

            return render_template('cart.html', product_data=product_data)
        else:
            product_data = dbs.product.find_one({'_id': ObjectId(product)})
            if request.args.get('methods') == 'buy':
                if request.args.get('mid') != session['id']:
                    session.clear()
                    return redirect(url_for('login'))
                dbs.member.update_one(
                    {
                        '_id': ObjectId(request.args.get('mid'))
                    },

                    {
                        '$set': {
                            'coin': member_data['coin']-product_data['price']
                        }

                    })
                dbs.product.update_one(
                    {
                        '_id': ObjectId(product)
                    },

                    {
                        '$set': {
                            'is_buy': True
                        }

                    })
                dbs.order.insert_one(
                    {
                        'product_id': ObjectId(product),
                        'mid': ObjectId(request.args.get('mid')),
                        'is_paid': False,
                        'prove_img': '',
                        'status': False
                    }
                )

                order_data = dbs.order.find_one({ 'product_id': ObjectId(product)})
                member_data = dbs.member.find_one({ "_id":ObjectId(request.args.get('mid')) })
                product_data = dbs.product.find_one({"_id":ObjectId(product)})

                payload = {
                    'oId': str(order_data['_id']),
                    'p_name': product_data['name'],
                    'bank_account': member_data['bankAccount']
                }

                res = requests.post('http://127.0.0.1:5001/api/v1/send_order', json=payload)
                res_data = res.json()

                dbs.order.update_one(
                    {
                        '_id': ObjectId(order_data['_id'])
                    },
                    {
                        '$set': {
                            'factory_id': res_data['data']['factory_id']
                        }
                    }
                )






                return redirect(url_for('cart', product='all'))
            else:
                return render_template('cart_order.html', product_data=product_data, member_data=member_data)

    else:
        return redirect(url_for('login'))


@app.route('/admin_user', methods=['GET', 'POST'])
def admin_user():
    if 'display_name' in session and session['display_name'] == '最高管理者':
        if request.method == 'POST':
            name = request.form['name']
            account = request.form['account']
            id = request.form['id']
            password = request.form['password']
            display_name = request.form['display_name']

            if id == '':
                user_data = dbs.bittop_admin.find_one({'account': account})
                if user_data != None:
                    return redirect('admin_user')
                salt = 'KKJNWSDJIJDJIWWIDJ'
                password_str = password + salt
                user_password = hashlib.sha1(password_str.encode('utf-8'))
                dbs.bittop_admin.insert_one({
                    'name': name,
                    'account': account,
                    'password': user_password.hexdigest(),
                    'salt': salt,
                    'display_name': display_name
                })
                return redirect('admin_user')
            else:
                user_data = dbs.bittop_admin.find_one({'_id': ObjectId(id)})
                if user_data['password'] != password:
                    password_str = password + user_data['salt']
                    user_password = hashlib.sha1(password_str.encode('utf-8'))
                    password = user_password.hexdigest()
                dbs.bittop_admin.update_one(
                    {
                        '_id': ObjectId(id)
                    },
                    {
                        '$set': {
                            'name': name,
                            'password': password,
                            'display_name': display_name

                        }
                    })
                return redirect('admin_user')
        else:
            if request.args.get('methods') == 'delete':
                dbs.bittop_admin.delete_one({"_id": ObjectId(request.args.get('id'))})
            user_data = []
            user_find = dbs.bittop_admin.find()
            for doc in user_find:
                doc['_id'] = str(doc['_id'])
                user_data.append(doc)
            return render_template('admin_user.html', user_data=user_data)
    else:
        return redirect('admin_dashboard')


@app.route('/admin_order',methods=['GET','POST'])
def admin_order():
    if 'display_name' and session['display_name'] == '最高管理者':
        match = {}
        page_data = {}
        orderNo_data = []
        print(request.method)
        if request.method =='POST':
            oId = request.form['no']
            is_paid = request.form['is_paid']
            name = request.form['name']
            
            if is_paid =='0' and is_paid != '':
                is_paid = False
            elif is_paid == '1' and is_paid !='':
                is_paid = True

            if oId != '':
                match['_id'] = ObjectId(oId)
            elif is_paid != '':
                match['is_paid'] = is_paid
            elif name != '':
                match['name'] = name

        if request.args.get('methods') == 'post':
            order_data = dbs.order.find_one(
                {
                    '_id': ObjectId(request.args.get('oid'))
                }
            )
            if order_data == None:
                session.clear()
                return redirect('admin_login')
            product_data = dbs.member_usdt.find_one(
                {'_id': ObjectId(order_data['product_id'])})
            member_data = dbs.member.find_one(
                {'_id': ObjectId(order_data['mid'])})

            dbs.member.update_one(
                {
                    '_id': ObjectId(member_data['_id'])
                },
                {
                    '$set': {
                        'real_coin': member_data['real_coin'] + int(product_data['price'])
                    }
                }
            )
            dbs.order.update_one(
                {
                    '_id': ObjectId(request.args.get('oid'))
                },
                {
                    '$set': {
                        'is_paid': True
                    }
                }
            )

            record_data = {
                'm_name': member_data['name'],
                'oId': str(order_data['_id']),
                'in_coin':  product_data['price'],
                'out_coin': 0,
                'in_bonus': 0,
                'out_bonus': 0
            }

            dbs.log_record.insert_one(record_data)

        elif request.args.get('methods') == 'delete':
            order_data = dbs.order.find_one(
                {
                    '_id': ObjectId(request.args.get('oid'))
                }
            )
            if order_data == None:
                session.clear()
                return redirect('admin_login')
            dbs.order.delete_one(
                {
                    '_id': ObjectId(request.args.get('oid'))
                }
            )

        elif request.args.get('methods') == 'setorderno':
            oid = request.args.get('oid')
            orderNo = request.args.get('orderno')
            order_data = dbs.order.find_one(
                {
                    "_id": ObjectId(oid)
                }
            )
            member_data = dbs.member.find_one(
                {
                    "_id": ObjectId(order_data['mid'])
                }
            )
            dbs.order.update_one(
                {
                    "_id": ObjectId(oid)
                },
                {
                    "$set": {
                        "order_detail": ObjectId(orderNo)
                    }
                }
            )
            print(orderNo)
            dbs.order_no.update_one(
                {
                    "_id": ObjectId(orderNo)
                },
                {
                    "$set": {
                        "is_used": True
                    },
                    "$push": {
                        "used_oid": member_data['bankAccount']
                    }
                }
            )
            return redirect('admin_order')

        current_page = request.args.get('page')
        skip = 0
        per = 4
        if current_page != None:
            skip = per * (int(current_page)-1)
        else:
            current_page = 1

        order_data = []
        order_len = dbs.order.count_documents(match)        
        if order_len % per == 0:
            all_page = order_len // per
        else:
            all_page = (order_len // per) + 1
        page_data['all_page'] = all_page
        page_data['current_page'] = current_page
        
        if 'is_paid' in match or 'name' in match:
            skip = 0
            per = 10000
            page_data = {}
       
        order_find = dbs.order.aggregate([
            {
                '$lookup': {
                    'from': 'product',
                    'localField': 'product_id',
                    'foreignField': '_id',
                    'as': 'product'
                }
            },
            {
                '$lookup': {
                    'from': 'member',
                    'localField': 'mid',
                    'foreignField': '_id',
                    'as': 'member'
                }
            },
            {
                '$match':match
            },
            {
                '$skip': skip
            },
            {
                '$limit': per
            }

        ])
        orderNo_find = dbs.order_no.find()
        for doc in orderNo_find:
            doc['_id'] = str(doc['_id'])
            if 'is_used' not in doc:
                orderNo_data.append(doc)

        for doc in order_find:
            doc['_id'] = str(doc['_id'])
            if 'order_detail' not in doc:
                doc['order_detail'] = False
            order_data.append(doc)

        return render_template('admin_order.html', order_data=order_data, page_data=page_data,
                               orderNo_data=orderNo_data )
    else:
        return redirect('admin_login')


@app.route('/admin_verify', methods=['GET', 'POST'])
def admin_verify():
    if 'display_name' and session['display_name'] == '最高管理者':
        if request.args.get('id'):
            if request.args.get('is_verify') == '1':
                dbs.bittop_member.update_one(
                    {
                        '_id': ObjectId(request.args.get('id'))
                    },
                    {
                        '$set': {
                            'is_verify': 1
                        }
                    }
                )
            else:
                dbs.bittop_member.update_one(
                    {
                        '_id': ObjectId(request.args.get('id'))
                    },
                    {
                        '$set': {
                            'is_verify': 2
                        }
                    }
                )

            return redirect('admin_verify')

        member_data = []
        member_find = dbs.bittop_member.find({
            'is_verify': 0
        })

        for doc in member_find:
            member_data.append(doc)

        return render_template('admin_verify.html', member_data=member_data)

    else:
        return redirect('admin_login')


@app.route('/admin_member', methods=['POST', 'GET'])
def admin_member():
    if 'display_name' and session['display_name'] == '最高管理者':
        if request.method == 'POST':
            name = request.form['name']
            USDT = float(request.form['USDT'])
            id = request.form['id']
            invitedCode = request.form['invitedCode']

            dbs.bittop_member.update_one(
                {
                    '_id': ObjectId(id)
                },
                {
                    '$set': {
                        'name': name,
                        'invitedCode': invitedCode,
                        'USDT': float(USDT),
                    }
                }
            )
            return redirect('admin_member')

        else:
            if request.args.get('methods') == 'delete':
                dbs.bittop_member.delete_one(
                    {
                        '_id': ObjectId(request.args.get('id'))
                    }
                )
            current_page = request.args.get('page')
            skip = 0
            per = 4
            if current_page != None:
                skip = per * (int(current_page)-1)
            else:
                current_page = 1
            member_data = []
            member_len = dbs.bittop_member.count_documents({})

            page_data = {}
            if member_len % per == 0:
                all_page = member_len // per
            else:
                all_page = (member_len // per) + 1
            page_data['all_page'] = all_page
            page_data['current_page'] = current_page
            
            bittop_member_find = dbs.bittop_member.find(
               {
                    'is_verify': 1
                },
               {
                    'password': 0,
                    'status': 0
                }
               )
            for doc in bittop_member_find:
                doc['_id'] = str(doc['_id'])
                member_data.append(doc)
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')

        try:
                # 如果提供了日期，则解析日期字符串为 datetime 对象
            if start_date and end_date:
                    start_date = datetime.strptime(start_date, '%Y-%m-%d')
                    end_date = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)
            else:
                    # 如果没有提供日期，使用默认的今日日期区间
                    start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
                    end_date = start_date + timedelta(days=1)

            # 为每个会员计算当日的usdtcount总和
            daily_volumes = {}
            logs = dbs.member_usdtlog.aggregate([
                {"$match": {
                    "date": {"$gte": start_date, "$lt": end_date},
                    "type": "售出"  # 筛选类型为"售出"的记录
                }},
                {"$group": {
                    "_id": "$account",
                    "total": {"$sum": "$usdtcount"}
                }}
            ])
            for log in logs:
                daily_volumes[log["_id"]] = log["total"]

            # 将计算得到的每日交易量添加到member_data中
            for member in member_data:
                account = member.get('account')
                member['daily_volume'] = daily_volumes.get(account, 0)

            return render_template("admin_member.html", member_data=member_data, page_data=page_data)
        except ValueError:
                # 处理无效日期输入的情况
                return "Invalid date format", 400

    else:
        return "Unauthorized", 401



@app.route('/admin_dashboard',methods=['GET', 'POST'])
def admin_dashboard():
    if 'display_name' in session:
        usdt_value = dbs.USDT.find_one()  # 获取USDT集合中的数据，调整查询以匹配您的数据结构
        if usdt_value:
        # 渲染模板并传递usdt值
            return render_template('admin_dashboard.html', usdt_rate=usdt_value['usdt'])
        else:
            return 'USDT值未找到', 404
    else:
        return redirect('admin_login')


@app.route('/get_member_count')
def get_member_count():
    member_count = dbs.bittop_member.count_documents({})
    return jsonify({'count': member_count})

@app.route('/get_pending_orders_count')
def get_pending_orders_count():
    pending_orders_count = dbs.member_usdt.count_documents({
        'is_buy': 0
    })

    return jsonify({'count': pending_orders_count})


@app.route('/get_total_usdt_sold_today')
def get_total_usdt_sold_today():
    # 获取当天的开始和结束时间
    tz = pytz.timezone('Asia/Taipei')  # 假设服务器在上海
    today_start = datetime.now(tz).replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timedelta(days=1)
    print(today_start)

    pipeline = [
        {
            '$match': {
                'type': '售出',
                # 使用date字段，并确保它是在当天
                'date': {'$gte': today_start, '$lt': today_end}
            }
        },
        {
            '$group': {
                '_id': None,
                'total': {'$sum': '$usdtcount'}  # 计算usdtcount的总和
            }
        }
    ]
    result = list(dbs.member_usdtlog.aggregate(pipeline))
    total_usdt_sold_today = result[0]['total'] if result else 0

    # 使用json_util来正确地序列化ObjectId和日期
    return json_util.dumps({'total_usdt_sold_today': total_usdt_sold_today})

# 设置Flask的JSON编码器


# @app.route('/member_dashboard',methods=['GET', 'POST'])
# def member_dashboard():
#     if 'display_name' in session:
#         return render_template('member_dashboard.html')
#     else:
#         return redirect('index')



@app.route('/order')
def order():
    if 'id' in session:
        if request.args.get('method') == 'success':
            oId = request.args.get('oId')
            pId = request.args.get('pId')
            product_data = dbs.product.find_one({
                '_id': ObjectId(pId),
            })
            order_data = dbs.order.find_one({
                '_id': ObjectId(oId),
            })
            if order_data == None or product_data == None:
                return redirect('order')
            member_data = dbs.member.find_one({
                '_id': ObjectId(session['id']),
            })

            record_data = {
                'm_name': member_data['name'],
                'oId': oId,
                'in_coin': 0,
                'out_coin': product_data['price'],
                'in_bonus': float(product_data['price'])*0.002,
                'out_bonus': 0
            }
            dbs.member.update_one(
                {
                    '_id': ObjectId(session['id']),
                },
                {
                    '$set': {
                        'bonus': member_data['bonus'] + float(product_data['price'])*0.002,
                        'real_coin': member_data['real_coin'] - product_data['price'],
                        'coin': member_data['coin'] + product_data['price']
                    }
                }
            )
            dbs.log_record.insert_one(record_data)
            dbs.order.update_one(
                {
                    '_id': ObjectId(oId)
                },
                {
                    '$set': {
                        'status': True
                    }
                }
            )
            return redirect('order')

        order_data = []
        order_find = dbs.order.aggregate([
            {
                '$match': {
                    'mid': ObjectId(session['id'])
                }
            },
            {
                '$lookup': {
                    'from': 'product',
                    'localField': 'product_id',
                    'foreignField': '_id',
                    'as': 'product'
                }
            }
        ])

        for doc in order_find:
            order_data.append(doc)
        return render_template('order.html', order_data=order_data)
    else:
        return redirect('login')
    
def find_ancestors(member, ancestors=[]):
    if 'invitedCode' in member and member['invitedCode']:
        superior = dbs.bittop_member.find_one({"account": member['invitedCode']})
        if superior and superior['account'] not in ancestors:
            ancestors.append(superior['account'])
            find_ancestors(superior, ancestors)
    return ancestors
def find_direct_descendants(member):
    # 直接下级
    direct_descendants = member.get('subordinates', [])
    return direct_descendants

def find_indirect_descendants(member, all_descendants=[]):
    # 间接下级
    if 'subordinates' in member and member['subordinates']:
        for subordinate_account in member['subordinates']:
            subordinate = dbs.bittop_member.find_one({"account": subordinate_account})
            if subordinate:
                if subordinate['account'] not in all_descendants:
                    all_descendants.append(subordinate['account'])
                    find_indirect_descendants(subordinate, all_descendants)
    # 移除直接下级
    direct_descendants = find_direct_descendants(member)
    return [descendant for descendant in all_descendants if descendant not in direct_descendants]

@app.route('/api/get_hierarchy', methods=['GET'])
def get_hierarchy():
    account = request.args.get('account')
    member = dbs.bittop_member.find_one({"account": account})
    if member:
        ancestors = find_ancestors(member, [])
        direct_descendants = find_direct_descendants(member)
        indirect_descendants = find_indirect_descendants(member, [])
        return jsonify(ancestors=ancestors, direct_descendants=direct_descendants, indirect_descendants=indirect_descendants)
    else:
        return jsonify(error='会员不存在'), 404
@app.route('/api/unprocessed-requests-count')

def get_unprocessed_requests_count():
    usdtPlus_collection = dbs.usdtPlus  # usdtPlus 集合
    usdtminus_collection = dbs.usdtminus  # usdtMinus 集合

    # 查询 status 为 False 的文档数量
    unprocessed_plus_count = usdtPlus_collection.count_documents({'status': False})
    unprocessed_minus_count = usdtminus_collection.count_documents({'status': False})

    total_unprocessed = unprocessed_plus_count + unprocessed_minus_count
    return jsonify(count=total_unprocessed)

@app.route('/api/member-usdt-count')
def get_member_usdt_count():
    member_usdt_collection = dbs.member_usdt  # 假设您有一个名为 member_usdt 的集合或表

    # 查询 is_buy 为 0 的文档数量
    is_buy_zero_count = member_usdt_collection.count_documents({'is_buy': 0})

    return jsonify(count=is_buy_zero_count)

@app.route('/api/memberverify-count')
def get_memberverify_count():
    member_collection = dbs.bittop_member

    # 查询  为 0 的文档数量
    is_verify_zero_count = member_collection.count_documents({'is_verify': 0})

    return jsonify(count=is_verify_zero_count)
    
@app.route('/admin_base', methods=['GET', 'POST'])
def admin_base():
    if 'account' in session :
        # 直接从会话中获取账号
        account = session.get('account', 'DefaultAccount')
        return render_template('admin_base.html', account="account")

    else:
        return redirect('admin_base')
    
        
@app.route('/member_base', methods=['GET', 'POST'])
def member_base():
    if 'account' in session :
        # 直接从会话中获取账号
        account = session.get('account', 'DefaultAccount')
        usdt = session.get('USDT', 'DefaultAccount')

        return render_template('member_base.html', account="account", usdt="USDT")

    else:
        return redirect('member_base')



@app.route('/admin_login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        admin_data = []
        account = request.form['account']
        password = request.form['password']
        potp = request.form['potp']
        session['account'] = account

        pottp_resul = verify_potp(potp)

        admin_find = dbs.bittop_admin.find({
            'account': account
        })
        for doc in admin_find:
            admin_data.append(doc)
        if len(admin_data) <= 0:
            return redirect('admin_login')
        password_str = password + admin_data[0]['salt']
        user_password = hashlib.sha1(password_str.encode('utf-8'))

        if admin_data[0]['password'] == user_password.hexdigest():
            session.permanent = True
            session['display_name'] = admin_data[0]['display_name']
            session['id'] = str(admin_data[0]['_id'])
            return redirect('admin_dashboard')
        else:
            return redirect('admin_login')
    else:
        if 'display_name' in session:
            return redirect('admin_dashboard')
        return render_template('admin_login.html')

@app.route('/memberdousdt', methods=['GET', 'PSOT'])
def memberdousdt():
    if 'account' in session:
        user_account = session['account']
        Taipei_tz = pytz.timezone('Asia/Taipei')

        # 获取当前的详细时间，并转换为不带时区的本地时间
        now_in_taipei = datetime.now(Taipei_tz)
        today_date = now_in_taipei.replace(tzinfo=None)  # 不带时区的当前时间

        # 处理 POST 请求
        if request.method == 'POST':
            account = session.get('account', 'DefaultAccount')
            usdt = session.get('USDT', 'DefaultAccount')
            usdtcount = request.form.get('usdtcount')
            tradecode = request.form.get('tradecode')
            tradetime = request.form.get('tradetime')
            # outtime = request.form.get('outtime')
            usdtout = request.form.get('usdtout')
            usdtaddress = request.form.get('usdtaddress')
            time = datetime.now(Taipei_tz).strftime('%Y-%m-%d %H:%M')  # 将时间转换为字符串格式
            status = request.form.get('status')

            if not request.form.get('id'):
                dbs.usdtPlus.insert_one({
                    'account': account,
                    'usdtcount': usdtcount,
                    'tradecode': tradecode,
                    'tradetime': tradetime,
                    'usdt': usdt,
                    'status':False,
                    'time':time,
                    'date': today_date  # 新增date字段

                }),
                dbs.usdtminus.insert_one({
                    'account': account,
                    # 'outtime': outtime,
                    'usdtout': usdtout, 
                    'usdtaddress': usdtaddress, 
                    'status':False,
                    'time':time,
                    'date': today_date  # 新增date字段



                }),

              
            else:
                dbs.usdtPlus.update_one(
                    {'_id': ObjectId(request.form.get('id'))},
                    {'$set': {
                        'account': account,
                        'usdtcount': usdtcount,
                        'tradecode': tradecode,
                        'tradetime': tradetime,
                        'usdt': usdt,
                        'time':time,

                        'status':False,
                        'date': today_date  # 新增date字段


                    }},
                )
                dbs.usdtminus.update_one(
                    {'_id': ObjectId(request.form.get('id'))},
                    {'$set': {
                    'account': account,
                    # 'outtime': outtime,
                    'usdtout': usdtout, 
                    'usdtaddress': usdtaddress, 
                    'time':time,
                    'status':False,
                    'date': today_date  # 新增date字段


                    }},
                )

            return redirect(url_for('memberdousdt'))
        
        # 处理 GET 请求
        else:
            if request.args.get('methods') == 'delete':
                dbs.usdtPlus.delete_one({'_id': ObjectId(request.args.get('id'))})
                dbs.usdtminus.delete_one({'_id': ObjectId(request.args.get('id'))})


            product_data = list(dbs.usdtPlus.find({'account': user_account}))
            withdraw_data = list(dbs.usdtminus.find({'account': user_account}))



            # 将每个文档中的 ObjectId 转换为字符串
            for item in product_data + withdraw_data:
                item['_id'] = str(item['_id'])
                if 'time' in item and isinstance(item['time'], datetime):
                    item['time'] = item['time'].strftime('%Y-%m-%d %H:%M:%S')
                elif 'date' in item and isinstance(item['date'], datetime):
                    item['date'] = item['date'].strftime('%Y-%m-%d ')


            return render_template('memberdousdt.html', product_data=json.dumps(product_data), withdraw_data=json.dumps(withdraw_data))

    else:
        return redirect(url_for('member_dashboard'))


@app.route('/rule1', methods=['GET', 'PSOT'])
def rule1():
    return render_template('rule1.html')
@app.route('/rule2', methods=['GET', 'PSOT'])
def rule2():
    return render_template('rule2.html')
@app.route('/admin_logout')
def admin_logout():
    session.clear()
    return redirect('admin_login')
@app.route('/member_logout')
def member_logout():
    session.clear()
    return redirect('/')


@app.route('/calculate_total_usdt')
def calculate_total_usdt():
    # 确保用户已登录
    if 'account' not in session:
        return jsonify({'error': '未登录'}), 401

    # 从数据库查询所有类型为"售出"的记录
    sales_records = dbs.member_usdtlog.find({'type': '售出'})

    # 计算总和
    total_usdt = sum(record.get('amount', 0) for record in sales_records)

    # 返回总和
    return jsonify({'total_usdt': total_usdt})

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        account = request.form["account"]
        password = request.form["password"]
        session['account'] = account

        # 检查 bittop_member 集合
        member = dbs.bittop_member.find_one({'account': account})

        # 如果用户在 bittop_member 集合中
        if member:
            # 检查会员是否通过审核
            if not member.get('is_verify', False):  # 替换 False 为指示未审核状态的值
                flash('会员尚未通过审核', 'warning')  # 显示警告消息
                return render_template('login.html')

            # 进行密码校验等操作
            password_str = password + member['salt']
            user_password = hashlib.sha1(password_str.encode('utf-8')).hexdigest()
            if member['password'] == user_password:
                # 设置会话变量
                session.permanent = True
                session['name'] = member['name']
                session['id'] = str(member['_id'])
                session['USDT'] = member['USDT']
                session['invitedCode'] = member['invitedCode']
                # 重定向到会员仪表盘
                return redirect('member_dashboard')
            else:
                # 如果密码不匹配
                flash('账号或密码错误', 'error')  # 显示错误消息
                return render_template('login.html')
        # 检查 bittop_admin 集合
        admin = dbs.bittop_admin.find_one({'account': account})

        # 如果用户在 bittop_admin 集合中
        if admin:
            # 进行密码校验等操作
            password_str = password + admin['salt']
            user_password = hashlib.sha1(password_str.encode('utf-8')).hexdigest()
            if admin['password'] == user_password:
                # 设置会话变量，可能需要不同的会话变量
                session.permanent = True
                session['name'] = admin['name']
                session['id'] = str(admin['_id'])
                # 重定向到管理员仪表盘
                return redirect('admin_dashboard')
            else:
                # 如果密码不匹配
                return render_template('login.html', error='帐号或密码错误')

        # 如果用户既不在 bittop_member 中也不在 bittop_admin 中
        flash('账号或密码错误', 'error')  # 显示错误消息
        return render_template('login.html')
    else:
        # 如果用户已登录，则根据角色重定向
        if 'id' in session:
            # 假设您有一个方式来确定用户的角色
            if is_member(session['id']):
                return redirect('member_dashboard')
            elif is_admin(session['id']):
                return redirect('admin_dashboard')
        return render_template('login.html')

def is_member(user_id):
    # 实现检查用户是否为会员的逻辑
    pass

def is_admin(user_id):
    # 实现检查用户是否为管理员的逻辑
    pass

@app.route('/some-endpoint')
def get_orders():
    orders = list(dbs.member_usdt.find())
    for order in orders:
        order['_id'] = str(order['_id'])
        # 假设图片URL存储在'image_url'字段中
        image_url = order.get('image_url', '')
        order['image_filename'] = os.path.basename(image_url) if image_url else 'No Image'
    return jsonify(orders)
@app.route('/admin_product', methods=['GET', 'POST'])
def admin_product():
    if 'display_name' in session:
        if request.method == 'POST':
            potp = request.form['potp']
            potp_result = verify_potp(potp)
            potp_result = True
            Taipei_tz = pytz.timezone('Asia/Taipei')

            # 获取当前的详细时间，并转换为不带时区的本地时间
            now_in_taipei = datetime.now(Taipei_tz)
            today_date = now_in_taipei.replace(tzinfo=None)  # 不带时区的当前时间

            if potp_result == True:
                account = request.form['account']
                price = request.form['price']
                total = request.form['total']
                min_limit = request.form['min_limit']
                max_limit = request.form['max_limit']
                time = request.form['time']
                P_bank = request.form['P_bank']
                is_buy = request.form['is_buy']




                if request.form['id'] == '':
                    dbs.member_usdt.insert_one(
                        {
                            'account': account,
                            'price': price,
                            'total': total,
                            'min_limit':min_limit,
                            'max_limit': max_limit,
                            'time': time,
                            'P_bank':P_bank,
                            'is_buy': False,
                            'date': today_date,  # 新增date字段
                            'is_buy': is_buy


                        }
                    )
                else:
                    dbs.member_usdt.update_one(
                        {
                            '_id': ObjectId(request.form['id'])
                        },
                        {
                            '$set': {
                            'account': account,
                            'price': price,
                            'total': total,
                            'min_limit':min_limit,
                            'max_limit': max_limit,
                            'P_bank':P_bank,
                            'date': today_date,  # 更新date字段
                            'time': time,
                            'is_buy': is_buy,
                         }
                        }
                    )

                return redirect('admin_product')
            else:
                return redirect('admin_product')
        else:
            if request.args.get('methods') == 'delete':
                dbs.member_usdt.delete_one(
                    {
                        '_id': ObjectId(request.args.get('id'))
                    }
                )
            product_data = []
            product_find = dbs.member_usdt.find().sort('date', -1)
            for doc in product_find:
                doc['_id'] = str(doc['_id'])
                product_data.append(doc)
            return render_template('admin_product.html', product_data=product_data)
    else:
        return redirect('admin_login')


@app.route('/api/upload-image', methods=['POST'])
def upload_image():
    try:
        image = request.files['image']
        order_id = request.form['id']

        if image and order_id and ObjectId.is_valid(order_id):
            upload_folder = '/path/to/upload/folder'  # 替换为您的实际存储路径
            if not os.path.exists(upload_folder):
                os.makedirs(upload_folder)

            filename = secure_filename(image.filename)
            path = os.path.join(upload_folder, filename)
            image.save(path)

            # 更新数据库记录
            image_url = url_for('static', filename=filename)
            result = dbs.member_usdt.update_one({'_id': ObjectId(order_id)}, {'$set': {'image_url': image_url}})
            
            print(f"Image saved to: {path}")
            print(f"Database update result: {result.raw_result}")

            return jsonify({'status': 'success', 'image_url': image_url})

        return jsonify({'status': 'error', 'message': 'Invalid data'})
    except Exception as e:
        traceback.print_exc()  # 打印完整的堆栈跟踪
        return jsonify({'status': 'error', 'message': str(e)})
    

    
@app.route('/test-db-update', methods=['GET'])
def test_db_update():
    try:
        # 假定的测试 ID 和更新内容
        test_id = '1234567890abcdef'
        test_update = {'$set': {'test_field': 'test_value'}}

        if ObjectId.is_valid(test_id):
            result = dbs.member_usdt.update_one({'_id': ObjectId(test_id)}, test_update)
            return jsonify({'status': 'success', 'result': str(result.raw_result)})
        else:
            return jsonify({'status': 'error', 'message': 'Invalid ID'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/confirm_order/<order_id>', methods=['POST'])
def confirm_order(order_id):
    try:
        # 获取订单信息
        order = dbs.member_usdt.find_one({'_id': ObjectId(order_id)})
        Taipei_tz = pytz.timezone('Asia/Taipei')

        # 获取当前的详细时间，并转换为不带时区的本地时间
        now_in_taipei = datetime.now(Taipei_tz)
        today_date = now_in_taipei.replace(tzinfo=None)  # 不带时区的当前时间

        
        if order and order.get('is_buy') == 0:
            # 更新订单状态
            dbs.member_usdt.update_one(
                {'_id': ObjectId(order_id)},
                {'$set': {'is_buy': 2}}
            )

            # 获取用户信息
            member_data = dbs.bittop_member.find_one({'account': order['account']})
            
            if member_data:
                updated_usdt = member_data['USDT'] - float(order['sell_usdt'])
                Taipei_tz = pytz.timezone('Asia/Taipei')
                now_in_taipei = datetime.now(Taipei_tz)
                
                # 将时区感知的当前台北时间转换为不带时区的本地时间
                local_now = now_in_taipei.replace(tzinfo=None)

                # 插入记录到 member_usdtlog
                dbs.member_usdtlog.insert_one({
                    'account': order['account'],
                    'usdtcount': order['sell_usdt'],
                    'time': local_now.strftime('%Y-%m-%d %H:%M'),  # 这里存储较少的时间信息
                    'type': '售出',
                    'date': local_now,  # 这里存储完整的当前时间（年月日时分秒）
                    'uptime': local_now.strftime('%Y-%m-%d %H:%M:%S'),
                    'USDT': updated_usdt  # 记录交易后的USDT余额
                })
                
                # 更新会员的USDT余额
                dbs.bittop_member.update_one(
                    {'account': order['account']},
                    {'$set': {'USDT': updated_usdt}}
                )

                return jsonify({'status': 'success'}), 200
            else:
                return jsonify({'status': 'error', 'message': '找不到用户信息'}), 404
        else:
            return jsonify({'status': 'error', 'message': '订单已被处理或不存在'}), 400

    except Exception as e:
        print("Error confirming order:", e)
        return jsonify({'status': 'error', 'message': '无法确认订单'}), 500

@app.route('/delete_card', methods=['POST'])
def delete_card():
    if 'account' in session:
        card_number = request.form.get('cardnumber')
        current_account = session['account']
        if card_number:
            # 根据cardnumber从数据库中删除指定的银行卡
            dbs.bittop_member.update_one(
                {'account': current_account},
                {'$pull': {'cards': {'cardnumber': card_number}}}
            )
            return jsonify({'success': True})
    return jsonify({'success': False}), 401

@app.route('/member_product', methods=['GET', 'POST'])
def member_product():
    if 'account' in session:
        current_account = session['account']

        # 获取当前用户的USDT信息和cards数组
        member_info = dbs['bittop_member'].find_one({'account': current_account})
        member_musdt = member_info.get('mUSDT', 0)
        bankcards = member_info.get('cards', []) if member_info else []
        Taipei_tz = pytz.timezone('Asia/Taipei')

        # 获取当前的详细时间，并转换为不带时区的本地时间
        now_in_taipei = datetime.now(Taipei_tz)
        today_date = now_in_taipei.replace(tzinfo=None)  # 不带时区的当前时间


        if request.method == 'POST':
            sell_usdt = request.form.get('sell_usdt', type=float)
            price = request.form.get('price', type=float)
            total = request.form.get('total', type=float)
            min_limit = request.form.get('min_limit', type=float)
            max_limit = request.form.get('max_limit', type=float)
            selected_card_number = request.form.get('banklist')  # 注意这里改为获取银行卡号

            if sell_usdt and sell_usdt <= member_musdt:
                # 从用户的cards数组中获取指定的银行卡信息
                card_info = next((card for card in bankcards if card.get('cardnumber') == selected_card_number), None)
                if not card_info:
                    flash('未找到指定的银行卡。')
                    print(card_info)
                    return redirect(url_for('member_product'))

                order_data = {
                    'account': current_account,
                    'sell_usdt': sell_usdt,
                    'price': price,
                    'total': total,
                    'min_limit': min_limit,
                    'max_limit': max_limit,
                    'time' : (datetime.now(Taipei_tz) + timedelta(hours=6)).strftime('%Y-%m-%d %H:%M'),
                    'is_buy': 0,
                    'P_bank': f"{card_info['bank']}_{card_info['cardnumber'][-6:]}",
                    'carddocument': card_info,
                    'USDT': member_musdt - sell_usdt,
                    'date': today_date  # 更新date字段

                }
                print(member_musdt - sell_usdt)

                # 创建新订单或更新现有订单
                order_id = request.form.get('id')
                print("Order ID:", order_id)
                if not order_id:
                    result = dbs['member_usdt'].insert_one(order_data)
                    print("Insert result:", result)
                else:
                    dbs['member_usdt'].insert_one(order_data)
                    result = dbs['member_usdt'].insert_one(order_data)
                    print("Insert result:", result)
                return redirect(url_for('member_product'))
            else:
                flash('无法上架，USDT余额不足或未指定USDT数量。')
                return redirect(url_for('member_product'))
        else:
            product_data = list(dbs['member_usdt'].find({'account': current_account}))
            # 转换每个文档中的ObjectId为字符串
            for product in product_data:
                product['_id'] = str(product['_id'])
            return render_template('member_product.html', bankcards=bankcards, member_usdt=member_musdt, product_data=product_data)

    else:
        return redirect(url_for('member_dashboard'))

@app.route('/api/submit_product', methods=['POST'])
def submit_product():
    if 'account' in session:
        current_account = session['account']
        
        # 从请求中获取JSON数据
        data = request.get_json()
        
        # 提取数据字段
        sell_usdt = data.get('sell_usdt')
        price = data.get('price')
        total = data.get('total')
        min_limit = data.get('min_limit')
        max_limit = data.get('max_limit')
        time = data.get('time')  # 从前端发送的时间
        card_number = data.get('card_number')  # 从前端发送的银行卡号
        
        # 从数据库获取当前用户信息和USDT余额
        # 假设 dbs['bittop_member'] 是你的数据库集合
        member_info = dbs['bittop_member'].find_one({'account': current_account})
        member_musdt = member_info['mUSDT'] if member_info else 0
        card_info = next((card for card in member_info.get('cards', []) if card.get('cardnumber') == card_number), None)

        # 如果卡信息不存在，返回错误
        if not card_info:
            return jsonify({'message': '未找到指定的银行卡。', 'status': 'error'}), 400

        # 如果USDT余额不足，返回错误
        if sell_usdt > member_musdt:
            return jsonify({'message': 'USDT余额不足。', 'status': 'error'}), 400

        # 构建订单数据
        new_usdt_balance = member_musdt - sell_usdt  # 更新后的USDT余额

        Taipei_tz = pytz.timezone('Asia/Taipei')

        # 获取当前的详细时间，并转换为不带时区的本地时间
        now_in_taipei = datetime.now(Taipei_tz)
        today_date = now_in_taipei.replace(tzinfo=None)  # 不带时区的当前时间

        order_data = {
            'account': current_account,
            'sell_usdt': sell_usdt,
            'price': price,
            'total': total,
            'min_limit': min_limit,
            'max_limit': max_limit,
            'time':  (datetime.now(Taipei_tz) + timedelta(hours=6)).strftime('%Y-%m-%d %H:%M'),
            'is_buy': 0,
            'P_bank': f"{card_info['bank']}_{card_number[-6:]}",
            'carddocument': card_info,
            'USDT': new_usdt_balance,
            'mUSDT':new_usdt_balance,
            'date': today_date # 更新date字段
        }
        insert_result = dbs['member_usdt'].insert_one(order_data)
        print("Insert result:", insert_result)

        if insert_result.inserted_id: 
        # 插入或更新订单数据到数据库
        # 假设 dbs['member_usdt'] 是你的订单数据集合
                update_result = dbs['bittop_member'].update_one(
                    {'account': current_account},
                    {'$set': {'mUSDT': new_usdt_balance}}
                )
                print("Update mUSDT result:", update_result)

        # 返回成功响应
        redirect_url = url_for('member_product')  # 'member_product' 是重定向的端点名

        return jsonify({'message': '产品提交成功', 'status': 'success' ,'redirect': redirect_url})
    else:
        # 如果用户未登录，返回错误
        return jsonify({'message': '用户未登录', 'status': 'error'}), 401
@app.route('/api/get_bank_cards', methods=['GET'])
def get_bank_cards():
    if 'account' in session:
        current_account = session['account']
        member_info = dbs['bittop_member'].find_one({'account': current_account})
        bankcards = member_info.get('cards', []) if member_info else []
        # 确保ObjectId被转换为字符串
        for card in bankcards:
            card['cardnumber'] = str(card['cardnumber'])
        return jsonify(bankcards)
    else:
        return jsonify([]), 401
@app.route('/update_rate', methods=['POST'])
def update_rate():
    if not session.get('account'):
        return jsonify({'error': '未登录'}), 401
    # 从请求中获取新汇率
    new_rate = request.json.get('rate')
    if new_rate:
        # 更新数据库中的汇率信息
        # 假设你有一个名为USDT的集合，它有一个字段叫做usdt来存储汇率
        dbs.USDT.update_one({}, {'$set': {'usdt': new_rate}})
        return jsonify({'message': '汇率更新成功'})
    else:
        return jsonify({'error': '无效的汇率值'}), 400

@app.route('/api/get_my_product_data')
def get_my_product_data():
    if 'account' not in session:
        # 如果用户未登录，返回错误信息
        return jsonify({'error': '未登录'}), 401

    # 获取当前登录用户的账号
    user_account = session['account']

    # 设置要从数据库检索的字段
    projection_fields = {
        'account': 1,
        'sell_usdt': 1,
        'price': 1,
        'total': 1,
        'min_limit': 1,
        'max_limit': 1,
        'time': 1,
        'is_buy': 1,
        'P_bank': 1,
        'date':1
    }

    # 从数据库查询当前用户的产品数据
    my_product_data = list(dbs.member_usdt.find({"account": user_account}, projection_fields))

    # 将ObjectId转换为字符串，以便进行JSON序列化
    for item in my_product_data:
        item['_id'] = str(item['_id'])

    # 返回JSON格式的响
    return jsonify(my_product_data)

@app.route('/api/get-all-product-data')
def get_all_product_data():
    # 查询字段设置
    projection_fields = {
        'account': 1,
        'sell_usdt': 1,
        'price': 1,
        'total': 1,
        'min_limit': 1,
        'max_limit': 1,
        'time': 1,
        'is_buy': 1,
        'date':1

    }

    # 从数据库查询数据
    all_product_data = list(dbs.member_usdt.find({}, projection_fields))

    # 将ObjectId转换为字符串，以便进行JSON序列化
    for item in all_product_data:
        item['_id'] = str(item['_id'])

    # 返回JSON格式的响应
    return jsonify(all_product_data)


@app.route('/order_prove', methods=['POST'])
def order_prove():
    if 'id' in session:
        oId = request.form['oId']
        f = request.files['prove_img']
        mid = session['id']
        member_data = dbs.member.find_one({'_id': ObjectId(mid)})
        account = member_data['account']
        imgUrl = ''

        if f and allowed_file(f.filename):
            file_path = basedir + '\public\image' + f'\{account}'
            if not os.path.isdir(file_path):
                os.mkdir(file_path)
            f.save(os.path.join(file_path, f.filename))
            imgUrl = f'/image/{account}/{f.filename}'

        dbs.order.update_one(
            {
                '_id': ObjectId(oId)
            },
            {
                '$set': {
                    'prove_img': imgUrl
                }
            }
        )

        return redirect('order')
    else:
        return redirect('login')

@app.route('/member_dashboard', methods=['GET', 'POST'])
def member_dashboard():
    if 'id' not in session:
        return redirect('login')

    current_user_id = session['id']
    member_data = dbs.bittop_member.find_one({'_id': ObjectId(current_user_id)})

    if not member_data:
        flash('No member data found.')
        return redirect('login')
    usdt_data = dbs.USDT.find_one()  # 调整为你的实际查询
    usdt_rate = usdt_data['usdt'] if usdt_data else 'Not Found'

    if request.method == 'GET':
        if request.args.get('method') == 'controlStatus':
            status = request.args.get('status') == "1"
            dbs.bittop_member.update_one(
                {'_id': ObjectId(current_user_id)},
                {'$set': {'status': status}}
            )

        user_qr_code = member_data.get('qr_code', None)

        # 获取更新后的用户信息和银行卡信息
        updated_member_data = dbs.bittop_member.find_one({'_id': ObjectId(current_user_id)})
        cards = updated_member_data.get('cards', [])

        # 渲染模板并传递更新后的数据
        return render_template('member_dashboard.html', user_qr_code=user_qr_code, member_data=updated_member_data, cards=cards,usdt_rate=usdt_rate)

    if request.method == 'POST':
        # 检查是否是删除操作
        delete_id = request.form.get('delete_id')
        if delete_id:
            try:
                # 删除指定的银行卡
                dbs.bittop_member.update_one(
                    {'_id': ObjectId(current_user_id)},
                    {'$pull': {'cards': {'_id': ObjectId(delete_id)}}}
                )
                flash('Card deleted successfully.')
            except Exception as e:
                print(f"Error deleting card: {e}")
                flash('Error occurred while deleting the card.')
            return redirect(url_for('member_dashboard'))

        # 处理添加银行卡请求
        bank = request.form.get('bank')
        branch = request.form.get('branch')
        bankprovince = request.form.get('bankprovince')
        accountname = request.form.get('accountname')
        cardnumber = request.form.get('cardnumber')

        if bank and branch and bankprovince and accountname and cardnumber:
            new_card_info = {
                'card_id': cardnumber,  # 生成唯一的card_id
                'bank': bank,
                'branch': branch,
                'bankprovince': bankprovince,
                'accountname': accountname,
                'cardnumber': cardnumber,
            }
            try:
                # 直接向 cards 数组中添加新的银行卡信息
                dbs.bittop_member.update_one(
                    {'_id': ObjectId(current_user_id)},
                    {'$push': {'cards': new_card_info}}
                )
                flash('Bank card added successfully.')
                return redirect(url_for('member_dashboard'))

            except Exception as e:
                print("Error adding card to bittop_member:", e)
                flash('Error occurred while adding the card.')
        delete_id = request.form.get('delete_id')
        if delete_id:
                try:
                    # 删除指定的银行卡
                    dbs.bittop_member.update_one(
                        {'_id': ObjectId(current_user_id)},
                        {'$pull': {'cards': {'card_id': delete_id}}}
                    )
                    flash('Card deleted successfully.')
                except Exception as e:
                    print(f"Error deleting card: {e}")
                    flash('Error occurred while deleting the card.')
                return redirect(url_for('member_dashboard'))

        return redirect(url_for('member_dashboard'))
 
 
    # 从数据库获取数据
    current_user = session['account']
    cards = current_user.get('cards', [])
    member_data = dbs.bittop_member.find_one({'_id': ObjectId(session['id'])})
    if not member_data:
        # 处理没有找到 member_data 的情况
        flash('No member data found.')
        return redirect(url_for('some_other_page'))

    for card in cards:
        card['_id'] = str(card['_id'])

    # 渲染模板并传递数据
    cards = member_data.get('cards', [])

    return render_template('member_dashboard.html', member_data=member_data)




@app.route('/recharge', methods=['POST']) # 确保使用POST方法
def recharge():
    tradetime = request.form.get('tradetime')
    tradecode = request.form.get('tradecode')
    usdtcount = request.form.get('usdtcount')
    account = session.get('account') # 假设会员账号存储在session中  

    if usdtcount and tradecode and account:
        try:
            # 获取当前时间
            Taipei_tz = pytz.timezone('Asia/Taipei')

            current_time = datetime.now(Taipei_tz).strftime('%Y-%m-%d %H:%M')
            Taipei_tz = pytz.timezone('Asia/Taipei')

            # 获取当前的详细时间，并转换为不带时区的本地时间
            now_in_taipei = datetime.now(Taipei_tz)
            today_date = now_in_taipei.replace(tzinfo=None)  # 不带时区的当前时间


            # 插入数据到数据库
            dbs.usdtPlus.insert_one({
                'account': account,
                'tradetime': tradetime,
                'usdtcount': usdtcount,
                'tradecode': tradecode,
                'time': current_time,  # 添加当前时间
                'status': False,
                'date': today_date  # 新增date字段

            })
        except Exception as e:
            print("Error inserting data:", e)
            # 可以选择在此处添加错误处理逻辑

    return redirect(url_for('member_dashboard'))
@app.route('/submit-usdt', methods=['POST'])
def submit_usdt():
    data = request.json
    account = session.get('account')  # 假设会员账号存储在session中
    if data.get('usdtcount') and data.get('tradecode') and account:
        try:
            # 获取当前时间
            Taipei_tz = pytz.timezone('Asia/Taipei')

            current_time = datetime.now(Taipei_tz).strftime('%Y-%m-%d %H:%M')
            Taipei_tz = pytz.timezone('Asia/Taipei')

            # 获取当前的详细时间，并转换为不带时区的本地时间
            now_in_taipei = datetime.now(Taipei_tz)
            today_date = now_in_taipei.replace(tzinfo=None)  # 不带时区的当前时间

            # 插入数据到数据库
            dbs.usdtPlus.insert_one({
                'account': account,
                'usdtcount': data.get('usdtcount'),
                'tradecode': data.get('tradecode'),
                'tradetime': data.get('tradetime'),
                'time': current_time,  # 添加当前时间
                'status': False,
                'date': today_date  # 新增date字段

            })
            return {"status": "success"}
        except Exception as e:
            print("Error inserting data:", e)
            return {"status": "error", "message": str(e)}, 500
    else:
        return {"status": "error", "message": "Missing data"}, 400

@app.route('/submit-withdraw', methods=['POST'])
def submit_withdraw():
    data = request.json
    account = session.get('account')

    if not account:
        return jsonify({"errorMessage": "未登录或会话已过期"}), 401

    if not data.get('usdtout') or not data.get('usdtaddress'):
        return jsonify({"errorMessage": "缺少必要的数据"}), 400

    user_data = dbs.bittop_member.find_one({'account': account})
    usdt_balance = user_data.get('mUSDT') if user_data else None

    if usdt_balance is None:
        return jsonify({"errorMessage": "无法获取用户余额"}), 500

    try:
        usdtout = float(data['usdtout'])
        if usdtout > usdt_balance:
            return jsonify({"errorMessage": "提领数量不能大于余额"}), 400

        # 更新用户的 USDT 余额
        new_balance = usdt_balance - usdtout
        dbs.bittop_member.update_one({'account': account}, {'$set': {'mUSDT': new_balance}})
        Taipei_tz = pytz.timezone('Asia/Taipei')

        current_time = datetime.now(Taipei_tz).strftime('%Y-%m-%d %H:%M')
        dbs.usdtminus.insert_one({
            'account': account,
            'usdtout': usdtout,
            'usdtaddress': data['usdtaddress'],
            'time': current_time,
            'status': False,
        })
        return jsonify({"status": "success"})
    except Exception as e:
        print("Error:", e)
        return jsonify({"status": "error", "message": "服务器错误"}), 500
@app.route('/get-withdraw-data')
def get_withdraw_data():
    try:
        newWithdrawal = list(dbs.usdtminus.find({}, {'_id': 0}))
        print("Retrieved withdrawData:", newWithdrawal)  # 打印检索到的数据
        return jsonify(newWithdrawal)
    except Exception as e:
        print("Error retrieving data:", e)
        return jsonify([]), 500

# @app.route('/profile', methods=['GET', 'POST'])
# def profile():
#     if 'id' in session:
#         if request.args.get('method') == 'controlStatus':
#             if request.args.get('status') == "1":
#                 status = True
#             else:
#                 status = False
#             print(status)
#             dbs.member.update_one(
#                 {
#                     '_id': ObjectId(session['id'])
#                 },
#                 {
#                     '$set': {
#                         'status': status
#                     }
#                 }

#             )
#             temp_data = dbs.member.find_one({'_id': ObjectId(session['id'])})
#             print(temp_data)
#             return redirect('profile')

#         member_data = dbs.member.find_one(
#             {
#                 '_id': ObjectId(session['id'])
#             },
#             {
#                 'password': 0
#             }
#         )

#         return render_template('profile.html', member_data=member_data)
#     else:
#         return redirect('login')
@app.route('/member_card', methods=['POST', 'GET'])
def member_card():
        if request.method == 'POST':
            real_coin = request.form['real_coin']
            bonus = request.form['bonus']
            bonus_rate = request.form['bonus_rate']
            name = request.form['name']
            coin = int(request.form['coin'])
            id = request.form['id']
            bankAccount = request.form['bankAccount']

            dbs.member_card.update_one(
                {
                    '_id': ObjectId(id)
                },
                {
                    '$set': {
                        'name': name,
                        'coin': coin,
                        'bankAccount': bankAccount,
                        'real_coin': int(real_coin),
                        'bonus': float(bonus),
                        'bonus_rate': float(bonus_rate)
                    }
                }
            )
            return redirect('member_card')

        else:
            if request.args.get('methods') == 'delete':
                dbs.member_card.delete_one(
                    {
                        '_id': ObjectId(request.args.get('id'))
                    }
                )
            current_page = request.args.get('page')
            skip = 0
            per = 4
            if current_page != None:
                skip = per * (int(current_page)-1)
            else:
                current_page = 1
            member_data = []
            member_len = dbs.member_card.count_documents({})

            page_data = {}
            if member_len % per == 0:
                all_page = member_len // per
            else:
                all_page = (member_len // per) + 1
            page_data['all_page'] = all_page
            page_data['current_page'] = current_page
            
            member_find = dbs.member_card.find(
               {
                    'is_verify': 1
                },
               {
                    'password': 0,
                    'status': 0
                }
               )
            for doc in member_find:
                doc['_id'] = str(doc['_id'])
                member_data.append(doc)

            return render_template("member_card.html", member_data=member_data,page_data=page_data)
        return redirect('member_card')


@app.route('/logout')
def logout():
    session.clear()
    return redirect('login')

@app.route('/admin_orderNo', methods=['GET', 'POST'])
def admin_orderNo():
    if 'display_name' in session:
        match = {}
        page_data = {}
        orderNo_data = []
        if request.method == 'POST':
            date = request.form['date']
            orderNo = request.form['orderNo']
            bankAccount = request.form['bankAccount']
            match = {
                "$or": [
                    {
                        "date": date
                    },
                    {
                        "order_no": orderNo
                    },
                    {
                        "used_oid": {
                            "$in": [bankAccount]
                        }
                    }
                ]          
            }

        orderNo_find = dbs.order_no.find(match)
        for doc in orderNo_find:
            doc['_id'] = str(doc['_id'])
            if doc['_id'] == '645253320dada5e817279de9':
                print(doc)
            if 'is_used' not in doc:
                doc['is_used'] = 'False'
            else:
                doc['is_used'] = 'True'
            orderNo_data.append(doc)
        return render_template('admin_orderNo.html', orderNo_data=orderNo_data, page_data=page_data)
    else:
        return redirect('admin_login')


# @app.route('/register', methods=['GET', 'POST'])
# def register():
#     if request.method == 'POST':
#         account = request.form['account']
#         password = request.form['password']
#         password2 = request.form['password2']
#         name = request.form['name']
#         resetPassword = request.form['resetPassword']
#         invitedCode = request.form['invitedCode']
#         display_name = request.form['display_name']
#         qr = qrcode.QRCode(
#             version=1,
#             error_correction=qrcode.constants.ERROR_CORRECT_L,
#             box_size=10,
#             border=4,
#         )
#         qr.add_data(f"http://127.0.0.1:5858/register?invite={account}")
#         qr.make(fit=True)
#         img = qr.make_image(fill_color="black", back_color="white")

#         # 将QR Code转换为base64编码的字符串
#         buffered = BytesIO()
#         img.save(buffered, format="PNG")
#         img_str = base64.b64encode(buffered.getvalue()).decode()


#         account_repeat = dbs.bittop_member.find_one({'account': account})
#         if account_repeat != None:
#             return redirect('register')

#         print(account, password,   name, resetPassword, password2,invitedCode)

#         salt = '645464'
#         password_str = password + salt
#         user_password = hashlib.sha1(password_str.encode('utf-8'))

#         dbs.bittop_member.insert_one({
#             'account': account,
#             'password': user_password.hexdigest(),
#             'password2':password2,
#             'name':  name,
#             'USDT': 0,
#             'bonus_rate': 0,
#             'status': False,
#             'is_verify': 0,
#             'salt': salt,
#             'invitedCode':invitedCode,
#             'qr_code': img_str,
#             'display_name':display_name,
#             'mUSDT':0,
#             'cards': [],
#         })

#         return render_template('success.html')
#     else:
#         return render_template('register.html')
    
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        # 获取表单数据
        account = request.form['account']
        password = request.form['password']
        name = request.form['name']
        resetPassword = request.form['resetPassword']
        invitedCode = request.form['invitedCode']
        display_name = request.form['display_name']

        # 检查账号是否已存在
        account_repeat = dbs['bittop_member'].find_one({'account': account})
        if account_repeat:
            flash('账号已存在')
            return redirect('register')

        # 检查邀请码是否有效
        inviter = dbs['bittop_member'].find_one({'account': invitedCode})
        if not inviter:
            flash('无效的邀请码')
            return redirect('register')

        # 生成二维码
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(f"http://bittop.store/register?invite={account}")
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")

        buffered = BytesIO()
        img.save(buffered)
        img_str = base64.b64encode(buffered.getvalue()).decode()

        # 处理密码
        salt = '645464'
        password_str = password + salt
        user_password = hashlib.sha1(password_str.encode('utf-8'))

        # 注册新用户
        dbs['bittop_member'].insert_one({
            'account': account,
            'password': user_password.hexdigest(),
            'name': name,
            'resetPassword': resetPassword,
            'USDT': 0,
            'bonus_rate': 0,
            'status': False,
            'is_verify': 0,
            'salt': salt,
            'invitedCode': invitedCode,
            'qr_code': img_str,
            'display_name': display_name,
            'mUSDT': 0,
            'cards': [],
            'subordinates': [],  # 初始化下级列表
        })

        # 更新邀请者的信息
        dbs['bittop_member'].update_one(
            {'account': invitedCode},
            {'$push': {'subordinates': account}}
        )

        return render_template('success.html')
    else:
        return render_template('register.html')
def verify_user(account):
    # 检索用户记录
    user = dbs.bittop_member.find_one({'account': account})
    if user and user['is_verify'] == 0:
        # 更新 is_verify
        dbs.bittop_member.update_one({'account': account}, {'$set': {'is_verify': 1}})
        # 找到相关的 usdtPlus 记录
        recharge_record = dbs.usdtPlus.find_one({'account': account, 'is_verify': 0})
        if recharge_record:
            usdtcount = recharge_record['usdtcount']
            # 更新 USDT 字段
            dbs.bittop_member.update_one({'account': account}, {'$inc': {'USDT': usdtcount}})
            # 更新 usdtPlus 记录的 is_verify
            dbs.usdtPlus.update_one({'account': account, 'is_verify': 0}, {'$set': {'is_verify': 1}})


@app.route('/api/<name>', methods=['GET', 'POST'])
def api(name):
  if name == 'fake_data' and request.method == 'GET':
    count = int(request.args.get('count'))
    fake_data = []
    number_list = random_number(count)
    for number in number_list:
      fake_find = dbs.fake_data.find_one({ "number": number }, { '_id': 0 })
      fake_data.append(fake_find)
    return jsonify(fake_data)
  elif name == 'factory_product' and request.method == 'POST':
    data = request.get_json()
    product_data = {
      "name": data['name'],
      "price": int(data['price']),
      "desc": "",
      "is_buy": False,
      "factory_bank": data['factory_bank'],
      "factory_name": data['factory_name']
    }
    dbs.product.insert_one(product_data)
    return jsonify({
      "message": "success"
    }), 200
  elif name == 'get_current_order':
    data = request.get_json()
    orderNo_data = []
    old_date = datetime.strptime(data['date'], '%Y-%m-%d')
    start_date = old_date + timedelta(days=1)
    start_date = start_date.strftime('%Y-%m-%d')
    end_date = old_date + timedelta(days=3)
    end_date = end_date.strftime('%Y-%m-%d')
    orderNo_find = dbs.order_no.find(
      {
        'date': {'$gte': start_date, '$lte': end_date}
      }
    )
    for doc in orderNo_find:
      repeat = False
      doc['_id'] = str(doc['_id'])
      for item in doc['used_oid']:
        if item == data['id']:
          repeat = True
      if repeat == False:
        orderNo_data.append(doc)
    return jsonify({
      'data': orderNo_data,
      'status': 'success'
    })
  else:
    return redirect(url_for('login'))
  
@app.route('/api/get_usdt_rate')
def get_usdt_rate():
    usdt_data = dbs.USDT.find_one()  # 调整为你的实际查询
    usdt_rate = usdt_data['usdt'] if usdt_data else 0
    print(usdt_rate)
    return jsonify({'usdt': usdt_rate})


if __name__ == "__main__":
    app.run(debug=True, use_reloader=False, port=5858)
