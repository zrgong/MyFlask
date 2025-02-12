# encoding=utf-8
import json
import datetime
from common.tail_font_log import FrontLogs
from flask.views import MethodView
from flask import render_template, Blueprint, request, g, redirect, url_for, current_app, jsonify, session
from modles.testcase import TestCases
from modles.case_group import CaseGroup
from modles.user import User
from modles.database import Mysql
from modles.request_headers import RequestHeaders
from common.rand_name import RangName
from common.analysis_params import AnalysisParams
from app import db
from common.connect_sqlite import cdb
from common.method_request import MethodRequest
from common.execute_testcase import to_execute_testcase
from common.request_get_more_values import request_get_values
from common.most_common_method import NullObject
from modles.variables import Variables

testcase_blueprint = Blueprint('testcase_blueprint', __name__)


class TestCaseLook(MethodView):

    def get(self, id=-1):
        testcase_id = request.args.get('id', id)
        user_id = session.get('user_id')
        print('testcase_id:', testcase_id)
        testcase = TestCases.query.get(testcase_id)
        if testcase.old_sql_id:
            old_mysql = Mysql.query.get(testcase.old_sql_id)
            old_mysql.name = AnalysisParams().analysis_params(old_mysql.name)
        else:
            old_mysql = ''
        if testcase.new_sql_id:
            new_mysql = Mysql.query.get(testcase.new_sql_id)
            new_mysql.name = AnalysisParams().analysis_params(new_mysql.name)
        else:
            new_mysql = ''
        case_groups = CaseGroup.query.all()
        case_group_id_before = testcase.group_id
        request_headers_id_before = testcase.request_headers_id
        request_headerses = RequestHeaders.query.all()
        FrontLogs('查看测试用例 name: %s ' % testcase.name).add_to_front_log()

        return render_template('test_case/test_case_look.html', item=testcase, case_groups=case_groups,
                               request_headers_id_before=request_headers_id_before,
                               case_group_id_before=case_group_id_before,
                               request_headerses=request_headerses, old_mysql=old_mysql, new_mysql=new_mysql)


class TestCaseRun(MethodView):

    def post(self):

        testcase_id, case_group_id, testcase_add_run, testcase_update_run \
            = request_get_values('testcase_id', 'case_group_id', 'testcase_add_run', 'testcase_update_run')
        testcase = TestCases.query.get(testcase_id)
        print('TestCaseRunForm: ', request.form)
        if testcase_update_run:
            testcase.name, testcase.url, testcase.data, testcase.method \
                = request_get_values('name', 'url', 'data', 'method')
        if testcase_add_run:
            testcase = NullObject()
            testcase.name, testcase.url, testcase.data, testcase.method, request_headers_id, \
            testcase.regist_variable, testcase.regular \
                = request_get_values('name', 'url', 'data', 'method', 'request_headers', 'regist_variable', 'regular')
            testcase.testcase_request_header = RequestHeaders.query.get(request_headers_id)
        testcase_results = []
        testcase_result, regist_variable_value = to_execute_testcase(testcase)
        # print('regist_variable_value', regist_variable_value)
        testcase_results.extend(['【%s】' % testcase.name, testcase_result, '【正则匹配的值】', regist_variable_value])
        testcase_results_html = '<br>'.join(testcase_results)
        # print('TestCaseRun testcase_results_html', testcase_results_html.encode('utf-8').decode('gbk'))
        FrontLogs('执行测试用例 name: %s ' % testcase.name).add_to_front_log()
        return json.dumps({'testcase_result': testcase_results_html})


class TestCastList(MethodView):

    def get(self):
        user_id = session.get('user_id')
        testcase_search = request_get_values('testcase_search')
        user = User.query.get(user_id)
        model_testcases = TestCases.query.filter(TestCases.is_model == 1, TestCases.user_id == user_id).all()
        # 过滤有测试用例分组的查询结果
        testcases = TestCases.query.filter(TestCases.testcase_scene_id.is_(None), TestCases.user_id == user_id).all()
        # 获取测试用例分组的列表
        print('testcases: ', testcases)
        for testcase in testcases:
            testcase.name = AnalysisParams().analysis_params(testcase.name)
            testcase.url = AnalysisParams().analysis_params(testcase.url)
            testcase.data = AnalysisParams().analysis_params(testcase.data)
        case_groups = user.user_case_groups
        print('case_groups: ', case_groups)
        request_headers = user.user_request_headers
        print('request_headers: ', request_headers)
        page = request.args.get('page', 1, type=int)
        #  pagination是salalchemy的方法，第一个参数：当前页数，per_pages：显示多少条内容 error_out:True 请求页数超出范围返回404错误 False：反之返回一个空列表
        pagination = TestCases.query.filter(TestCases.name.like(
            "%" + testcase_search + "%") if testcase_search is not None else "",
                                            TestCases.testcase_scene_id.is_(None),
                                            TestCases.user_id == user_id).order_by \
            (TestCases.timestamp.desc()).paginate(
            page, per_page=current_app.config['FLASK_POST_PRE_ARGV'], error_out=False)
        # 返回一个内容对象
        testcaseses = pagination.items
        print("pagination: ", pagination)
        FrontLogs('进入测试用例列表页面 第%s页' % page).add_to_front_log()
        return render_template('test_case/test_case_list.html', pagination=pagination, items=testcaseses,
                               case_groups=case_groups,
                               request_headers=request_headers, page=page, model_testcases=model_testcases)


class TestCaseAdd(MethodView):

    def get(self):
        user_id = session.get('user_id')
        user = User.query.get(user_id)
        mysqls = Mysql.query.all()
        for mysql in mysqls:
            mysql.ip, mysql.port, mysql.name, mysql.user, mysql.password = AnalysisParams().analysis_more_params(
                mysql.ip, mysql.port, mysql.name, mysql.user, mysql.password
            )
        page, scene_page = request_get_values('page', 'scene_page')
        case_groups = user.user_case_groups
        testcase_scene_id = request.args.get('testcase_scene_id', None)
        request_headers_querys_sql = 'select id,name from request_headers where user_id=?'
        request_headers = cdb().query_db(request_headers_querys_sql, (user_id,))
        print('request_headers: ', request_headers)
        FrontLogs('进入添加测试用例页面').add_to_front_log()
        return render_template('test_case/test_case_add.html', case_groups=case_groups,
                               request_headers=request_headers, testcase_scene_id=testcase_scene_id,
                               scene_page=scene_page, page=page, mysqls=mysqls)

    def post(self):
        user_id = session.get('user_id')
        print('要添加的测试用例：', request.form)
        page, scene_page, name, url, method, regist_variable, regular, request_headers_id, old_sql, new_sql, \
        old_sql_regist_variable, new_sql_regist_variable, old_sql_hope_result, new_sql_hope_result, old_mysql_id, \
        new_mysql_id = \
            request_get_values('page', 'scene_page', 'name', 'url', 'method',
                               'regist_variable', 'regular', 'request_headers', 'old_sql', 'new_sql',
                               'old_sql_regist_variable', 'new_sql_regist_variable', 'old_sql_hope_result',
                               'new_sql_hope_result', 'old_mysql', 'new_mysql')
        group_id = request.form.get('case_group', None)
        data = request.form.get('data', '').replace('/n', '').replace(' ', '')

        request_headers_query_sql = 'select value from request_headers where id=?'
        request_headers = cdb().query_db(request_headers_query_sql, (request_headers_id,), True)[0]
        print('TestCaseAdd request_headers before: ', request_headers, method)
        request_headers = AnalysisParams().analysis_params(request_headers, is_change="headers")
        print('TestCaseAdd request_headers: ', request_headers)
        testcase_scene_id = request.args.get('testcase_scene_id', None)
        if testcase_scene_id == "None":
            testcase_scene_id = None
        print('testcase_scene_id的值：', testcase_scene_id, type(testcase_scene_id))
        headers = json.loads(request_headers)
        print('request_headers_id: %s headers:%s ' % (request_headers_id, headers))
        hope_result = request.form.get('hope_result')
        if request.form.get('test', 0) == '测试':
            data = RangName(data).rand_str()
            url = AnalysisParams().analysis_params(url)
            result = MethodRequest().request_value(method, url, data, headers).replace('<', '').replace('>', '')
            return '''%s''' % result

        print('testcase_scene_id的值：', testcase_scene_id, type(testcase_scene_id))
        testcase = TestCases(
            name, url, data, regist_variable, regular, method, group_id,
            request_headers_id, hope_result=hope_result,
            testcase_scene_id=testcase_scene_id, user_id=user_id, old_sql=old_sql, new_sql=new_sql,
            old_sql_regist_variable=old_sql_regist_variable, new_sql_regist_variable=new_sql_regist_variable,
            old_sql_hope_result=old_sql_hope_result, new_sql_hope_result=new_sql_hope_result, old_mysql_id=old_mysql_id,
            new_mysql_id=new_mysql_id)
        add_regist_variable(old_sql_regist_variable, new_sql_regist_variable, user_id)
        db.session.add(testcase)
        db.session.commit()
        FrontLogs('添加测试用例 name: %s 成功' % name).add_to_front_log()
        # app.logger.info('message:insert into testcases success, name: %s' % name)
        if testcase_scene_id not in (None, "None"):
            return redirect(url_for('testcase_scene_blueprint.testcase_scene_testcase_list', page=scene_page))
        return redirect(url_for('testcase_blueprint.test_case_list', page=page))


class UpdateTestCase(MethodView):

    def get(self, id=-1):
        user_id = session.get('user_id')
        user = User.query.get(user_id)
        page = request_get_values('page')
        mysqls = Mysql.query.filter(Mysql.user_id == user_id).all()
        for mysql in mysqls:
            mysql.name = AnalysisParams().analysis_params(mysql.name)
        testcase_scene_id = request.args.get('testcase_scene_id', None)
        scene_page = request.args.get('scene_page')
        print('UpdateTestCase get:testcase_scene_id ', testcase_scene_id)
        testcase = TestCases.query.filter(TestCases.id == id).first()
        print('testcase.group_id:', testcase.group_id)
        # 获取测试用例分组的列表
        case_groups = user.user_case_groups
        case_group_id_before = testcase.group_id
        request_headers_id_before = testcase.request_headers_id
        request_headerses = user.user_request_headers
        print('testcase:', testcase)
        print('case_groups :', case_groups)
        print('request_headerses:', request_headerses)
        FrontLogs('进入编辑测试用例 id: %s 页面' % id).add_to_front_log()
        return render_template('test_case/test_case_search.html', item=testcase, case_groups=case_groups,
                               request_headers_id_before=request_headers_id_before,
                               case_group_id_before=case_group_id_before,
                               request_headerses=request_headerses, testcase_scene_id=testcase_scene_id,
                               scene_page=scene_page, page=page, mysqls=mysqls)

    def post(self, id=-1):
        page, scene_page, name, url, method, data, group_id, request_headers_id, regist_variable, regular \
            , hope_result, testcase_scene_id, old_sql, new_sql, old_sql_regist_variable, new_sql_regist_variable, \
            old_sql_hope_result, new_sql_hope_result, old_mysql_id, new_mysql_id = request_get_values(
            'page', 'scene_page', 'name', 'url', 'method', 'data', 'case_group', 'request_headers', 'regist_variable',
            'regular', 'hope_result', 'testcase_scene_id', 'old_sql', 'new_sql', 'old_sql_regist_variable',
            'new_sql_regist_variable', 'old_sql_hope_result', 'new_sql_hope_result', 'old_mysql', 'new_mysql')
        print('UpdateTestCase post:testcase_scene_id ', testcase_scene_id, scene_page)
        id = request.args.get('id', id)
        user_id = session.get('user_id')
        update_regist_variable(id, old_sql_regist_variable, new_sql_regist_variable, user_id)
        update_test_case_sql = 'update testcases set name=?,url=?,data=?,method=?,group_id=?,' \
                               'request_headers_id=?,regist_variable=?,regular=?,hope_result=?,' \
                               'old_sql=?,new_sql=?,old_sql_regist_variable=?,new_sql_regist_variable=?,' \
                               'old_sql_hope_result=?, new_sql_hope_result=?, old_sql_id=?, new_sql_id=? where id=?'
        cdb().opeat_db(update_test_case_sql, (name, url, data, method, group_id,
                                              request_headers_id, regist_variable, regular, hope_result, old_sql,
                                              new_sql, old_sql_regist_variable, new_sql_regist_variable,
                                               old_sql_hope_result, new_sql_hope_result, old_mysql_id, new_mysql_id, id))

        FrontLogs('编辑测试用例 name: %s 成功' % name).add_to_front_log()
        # app.logger.info('message:update testcases success, name: %s' % name)
        print('UpdateTestCase post:testcase_scene_id return :', testcase_scene_id, len(testcase_scene_id))
        if testcase_scene_id not in (None, "None"):
            print('UpdateTestCase post:testcase_scene_id return :', testcase_scene_id is True, len(testcase_scene_id))
            return redirect(url_for('testcase_scene_blueprint.testcase_scene_testcase_list', page=scene_page))
        return redirect(url_for('testcase_blueprint.test_case_list', page=page))


class TestCaseCopy(MethodView):

    def get(self):
        page, testcase_id = request_get_values('page', 'testcase_id')
        testcase_self = TestCases.query.get(testcase_id)

        timestr = str(datetime.datetime.now().strftime('%Y%m%d%H%M%S'))
        name = testcase_self.name + timestr
        db.session.add(TestCases(name, testcase_self.url, testcase_self.data, testcase_self.regist_variable,
                                 testcase_self.regular, testcase_self.method, testcase_self.group_id,
                                 testcase_self.request_headers_id, hope_result=testcase_self.hope_result,
                                 user_id=testcase_self.user_id, old_sql=testcase_self.old_sql,
                                 new_sql=testcase_self.old_sql, old_sql_regist_variable=testcase_self.old_sql_regist_variable,
                                 new_sql_regist_variable=testcase_self.new_sql_regist_variable, old_sql_hope_result=testcase_self.old_sql_hope_result,
                                 new_sql_hope_result=testcase_self.new_sql_hope_result,old_sql_id=testcase_self.old_sql_id,
                                 new_sql_id=testcase_self.new_sql_id))
        db.session.commit()
        FrontLogs('复制测试用例 name: %s 为模板成功' % testcase_self.name).add_to_front_log()
        return redirect(url_for('testcase_blueprint.test_case_list', page=page))


class DeleteTestCase(MethodView):

    def get(self, id=-1):
        page, scene_page = request_get_values('page', 'scene_page')
        testcase_scene_id = request.args.get('testcase_scene_id', None)
        delete_test_case_sql = 'delete from testcases where id=?'
        cdb().opeat_db(delete_test_case_sql, (id,))
        FrontLogs('删除测试用例 id: %s 成功' % id).add_to_front_log()
        # app.logger.info('message:delete testcases success, id: %s' % id)
        if testcase_scene_id not in (None, "None"):
            return redirect(url_for('testcase_scene_blueprint.testcase_scene_testcase_list', page=scene_page))
        return redirect(url_for('testcase_blueprint.test_case_list', page=page))


class ModelTestCase(MethodView):

    def get(self, id=-1):
        testcase = TestCases.query.get(id)
        page = request.args.get('page')
        if testcase.is_model == 0:
            testcase.is_model = 1
            FrontLogs('设置测试用例 name: %s 为模板成功' % testcase.name).add_to_front_log()
        else:
            testcase.is_model = 0
            FrontLogs('取消设置测试用例 name: %s 为模板成功' % testcase.name).add_to_front_log()
        db.session.commit()
        return redirect(url_for('testcase_blueprint.test_case_list', page=page))


class TestCaseValidata(MethodView):

    def get(self):
        user_id = session.get('user_id')
        name = request.args.get('name')
        testcase = TestCases.query.filter(TestCases.name == name, TestCases.user_id == user_id).count()
        if testcase != 0:
            return jsonify(False)
        else:
            return jsonify(True)


class TestCaseUpdateValidata(MethodView):

    def get(self):
        user_id = session.get('user_id')
        name, testcase_id = request_get_values('name', 'testcase_id')
        testcase = TestCases.query.filter(
            TestCases.id != testcase_id).filter(TestCases.name == name, TestCases.user_id == user_id).count()
        if testcase != 0:
            return jsonify(False)
        else:
            return jsonify(True)


class TestCaseHopeResultValidata(MethodView):

    def get(self):
        hope_result = request.args.get('hope_result')
        print('hope_result: ', hope_result)
        try:
            com_method, _ = hope_result.split(':', 1)
            if com_method == "包含":
                return jsonify(True)
            else:
                return jsonify(False)
        except Exception as e:
            print(e)
            return jsonify(False)


testcase_blueprint.add_url_rule('/testcaselist/', view_func=TestCastList.as_view('test_case_list'))
testcase_blueprint.add_url_rule('/addtestcase/', view_func=TestCaseAdd.as_view('add_test_case'))
testcase_blueprint.add_url_rule('/deletetestcase/<id>/', view_func=DeleteTestCase.as_view('delete_test_case'))
testcase_blueprint.add_url_rule('/updatetestcase/<id>/', view_func=UpdateTestCase.as_view('update_test_case'))
testcase_blueprint.add_url_rule('/testcase_model/<id>/', view_func=ModelTestCase.as_view('test_case_model'))
testcase_blueprint.add_url_rule('/look_test_case/<id>/', view_func=TestCaseLook.as_view('look_test_case'))
testcase_blueprint.add_url_rule('/run_test_case/', view_func=TestCaseRun.as_view('run_test_case'))
testcase_blueprint.add_url_rule('/copy_test_case/', view_func=TestCaseCopy.as_view('copy_test_case'))

testcase_blueprint.add_url_rule('/testcasevalidate/', view_func=TestCaseValidata.as_view('testcase_validate'))
testcase_blueprint.add_url_rule('/testcaseupdatevalidate/',
                                view_func=TestCaseUpdateValidata.as_view('testcase_update_validate'))
testcase_blueprint.add_url_rule('/test_case_hope_result_validate/',
                                view_func=TestCaseHopeResultValidata.as_view('test_case_hope_result_validate'))


def add_regist_variable(old_sql_regist_variable, new_sql_regist_variable, user_id):
    if old_sql_regist_variable:
        old_variable = Variables(old_sql_regist_variable, '', user_id=user_id, is_private=1)
        db.session.add(old_variable)
    if new_sql_regist_variable:
        new_variable = Variables(new_sql_regist_variable, '', user_id=user_id, is_private=1)
        db.session.add(new_variable)


def update_regist_variable(testcase_id, old_sql_regist_variable, new_sql_regist_variable, user_id):
    testcase = TestCases.query.get(testcase_id)
    if testcase.old_sql_regist_variable:
        Variables.query.filter(Variables.name == testcase.old_sql_regist_variable,
                               Variables.user_id == user_id).first().name = old_sql_regist_variable
    if testcase.new_sql_regist_variable:
        Variables.query.filter(Variables.name == testcase.new_sql_regist_variable,
                               Variables.user_id == user_id).first().name = new_sql_regist_variable
    db.session.commit()