from modles.case_group import CaseGroup
from modles.mail import Mail
from modles.request_headers import RequestHeaders
from modles.variables import Variables
from modles.user import User
from app import db
from common.connect_sqlite import cdb
from pre_data import variable as var
from pre_data.variable import *
from pre_data import user
from pre_data.user import *
from pre_data import case_group
from pre_data.case_group import *
from pre_data import mail
from pre_data.mail import *
from pre_data import request_headers
from pre_data.request_headers import *


def add_pre_data(key, user_id, table=None):
    # 根据需要插入的表明  进行预配置参数插入
    if table is None:
        table = ["Variavles", ]
    print('add_pre_data user_id:', user_id)
    print('key:', key, eval(key))
    var_name = "_%s" % key
    if "Variavles" in table:
        if Variables.query.filter(Variables.name == "%s" % var_name, Variables.user_id == user_id).count() == 0:
            print('Variables.query.filter user_id:', user_id)
            instance = Variables(var_name, eval(key), user_id=user_id)
            db.session.add(instance)
            db.session.commit()

    elif 'User' in table:
        username, password = eval(key)
        if User.query.filter(User.username == "%s" % username).count() == 0:
            _user = User(username, password)
            db.session.add(_user)
            db.session.commit()

    elif 'CaseGroup' in table:
        name = eval(key)
        if CaseGroup.query.filter(CaseGroup.name == "%s" % name).count() == 0:
            _case_group = CaseGroup(name)
            db.session.add(_case_group)
            db.session.commit()

    elif 'Mail' in table:
        name = eval(key)
        if Mail.query.filter(Mail.name == "%s" % name).count() == 0:
            _mail = Mail(name)
            db.session.add(_mail)
            db.session.commit()

    elif 'RequestHeaders' in table:
        name, value = eval(key)
        if RequestHeaders.query.filter(RequestHeaders.name == "%s" % name).count() == 0:
            _request_headers = RequestHeaders(name, value)
            db.session.add(_request_headers)
            db.session.commit()


def add_pre_data_go(user_id):
    print('add_pre_data_go user_id:', user_id)
    pre_variable = dir(user)
    # 获取var模块的所有属性
    [add_pre_data(key, user_id, table='User') for key in pre_variable if "__" not in key and key[0].isupper()]

    pre_variable = dir(var)
    # 获取var模块的所有属性
    [add_pre_data(key, user_id) for key in pre_variable if "__" not in key and key[0].isupper()]
    # 通过列表生成式 过滤首字符非大写，没有__的变量

    pre_variable = dir(mail)
    [add_pre_data(key, user_id, table='Mail') for key in pre_variable if "__" not in key and key[0].isupper()]

    pre_variable = dir(case_group)
    [add_pre_data(key, user_id, table='CaseGroup') for key in pre_variable if "__" not in key and key[0].isupper()]

    pre_variable = dir(request_headers)
    [add_pre_data(key, user_id, table='RequestHeaders') for key in pre_variable if "__" not in key and key[0].isupper()]


def to_insert_data(user_id=1):
    add_pre_data_go(user_id=user_id)


# if __name__ == '__main__':
#     add_pre_user()
