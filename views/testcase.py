import json
from common.tail_font_log import FrontLogs
from flask.views import MethodView
from flask import render_template, Blueprint, request, redirect, url_for, current_app, jsonify
from modles.testcase import TestCases
from modles.case_group import CaseGroup
from modles.request_headers import RequestHeaders
from common.rand_name import RangName
from common.analysis_params import AnalysisParams
from app import cdb, db, app
from common.method_request import MethodRequest
from common.execute_testcase import to_execute_testcase
from common.request_get_more_values import request_get_values

testcase_blueprint = Blueprint('testcase_blueprint', __name__)


class TestCaseLook(MethodView):

    def get(self, id=-1):
        testcase_id = request.args.get('id', id)
        print('testcase_id:', testcase_id)
        testcase = TestCases.query.get(testcase_id)
        case_groups = CaseGroup.query.all()
        case_group_id_before = testcase.group_id
        request_headers_id_before = testcase.request_headers_id
        request_headerses = RequestHeaders.query.all()

        return render_template('test_case/test_case_look.html', item=testcase, case_groups=case_groups,
                               request_headers_id_before=request_headers_id_before, case_group_id_before=case_group_id_before,
                               request_headerses=request_headerses)


class TestCaseRun(MethodView):

    def get(self):
        testcase_id = request.args.get('testcase_id', 0)
        testcase = TestCases.query.get(testcase_id)
        testcase_results = []
        testcase_result = to_execute_testcase(testcase)
        testcase_results.extend(['【%s】' % testcase.name, testcase_result])
        testcase_results_html = '<br>'.join(testcase_results)
        print('TestCaseRun testcase_results_html', testcase_results_html)
        return json.dumps({'testcase_result': testcase_results_html})


class TestCastList(MethodView):

    def get(self):
        # sql = 'select ROWID,id,name,url,data,result,method,group_id from testcases'
        # tests = cdb().query_db(sql)
        # 过滤有测试用例分组的查询结果
        testcases = TestCases.query.filter(TestCases.testcase_scene_id.is_(None)).all()
        # 获取测试用例分组的列表
        print('testcases: ', testcases)
        for testcase in testcases:
            testcase.name = AnalysisParams().analysis_params(testcase.name)
            testcase.url = AnalysisParams().analysis_params(testcase.url)
            testcase.data = AnalysisParams().analysis_params(testcase.data)
        case_groups = CaseGroup.query.all()
        print('case_groups: ', case_groups)
        request_headers = RequestHeaders.query.all()
        print('request_headers: ', request_headers)
        page = request.args.get('page', 1, type=int)
        #  pagination是salalchemy的方法，第一个参数：当前页数，per_pages：显示多少条内容 error_out:True 请求页数超出范围返回404错误 False：反之返回一个空列表
        pagination = TestCases.query.filter(TestCases.testcase_scene_id.is_(None)).order_by(TestCases.timestamp.desc()).paginate(page, per_page=current_app.config[
            'FLASK_POST_PRE_ARGV'], error_out=False)
        # 返回一个内容对象
        testcaseses = pagination.items
        print("pagination: ", pagination)
        FrontLogs('进入测试用例列表页面 第%s页' % page).add_to_front_log()
        return render_template('test_case/test_case_list.html', pagination=pagination, items=testcaseses, case_groups=case_groups,
                               request_headers=request_headers)


class TestCaseAdd(MethodView):

    def get(self):
        case_groups_querys_sql = 'select id,name from case_group'
        case_groups = cdb().query_db(case_groups_querys_sql)
        testcase_scene_id = request.args.get('testcase_scene_id', None)
        request_headers_querys_sql = 'select id,name from request_headers'
        request_headers = cdb().query_db(request_headers_querys_sql)
        print('request_headers: ', request_headers )
        FrontLogs('进入添加测试用例页面').add_to_front_log()
        return render_template('test_case/test_case_add.html', case_groups=case_groups,
                               request_headers=request_headers, testcase_scene_id=testcase_scene_id)

    def post(self):
        print('要添加的测试用例：', request.form)
        name, url, method, group_id, regist_variable, regular, request_headers_id = request_get_values(
            'name', 'url', 'method', 'case_group', 'regist_variable', 'regular', 'request_headers')

        data = request.form.get('data', None).replace('/n', '').replace(' ', '')

        request_headers_query_sql = 'select value from request_headers where id=?'
        request_headers = cdb().query_db(request_headers_query_sql, (request_headers_id,), True)[0]
        print('TestCaseAdd request_headers before: ', request_headers)
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
        query_all_names_sql = 'select name from testcases'
        all_names = cdb().query_db(query_all_names_sql)
        print(all_names)
        if (name,) in all_names:
            return '已有相同测试用例名称，请修改'
        else:
            print('testcase_scene_id的值：', testcase_scene_id, type(testcase_scene_id))
            testcase = TestCases(
                name, url, data, regist_variable, regular, method, group_id, 
                request_headers_id,hope_result=hope_result, 
                testcase_scene_id=testcase_scene_id)
            db.session.add(testcase)
            db.session.commit()
            FrontLogs('添加测试用例 name: %s 成功' % name).add_to_front_log()
            app.logger.info('message:insert into testcases success, name: %s' % name)
            if testcase_scene_id not in(None, "None"):
                return redirect(url_for('testcase_scene_blueprint.testcase_scene_testcase_list'))
            return redirect(url_for('testcase_blueprint.test_case_list'))


class UpdateTestCase(MethodView):

    def get(self, id=-1):
        testcase_scene_id = request.args.get('testcase_scene_id', None)
        print('UpdateTestCase get:testcase_scene_id ', testcase_scene_id)
        testcase = TestCases.query.filter(TestCases.id == id).first()
        print('testcase.group_id:', testcase.group_id)
        # 获取测试用例分组的列表
        case_groups = CaseGroup.query.all()
        case_group_id_before = testcase.group_id
        request_headers_id_before = testcase.request_headers_id
        request_headerses = RequestHeaders.query.all()
        print('testcase:', testcase)
        print('case_groups :', case_groups)
        print('request_headerses:', request_headerses)
        FrontLogs('进入编辑测试用例 id: %s 页面' % id).add_to_front_log()
        return render_template('test_case/test_case_search.html', item=testcase, case_groups=case_groups,
                               request_headers_id_before=request_headers_id_before, case_group_id_before=case_group_id_before,
                               request_headerses=request_headerses, testcase_scene_id=testcase_scene_id)

    def post(self, id=-1):
        name, url, method, data, group_id, request_headers_id, regist_variable, regular, hope_result, testcase_scene_id = \
            request_get_values('name', 'url', 'method', 'data', 'case_group', 'request_headers',
                               'regist_variable', 'regular', 'hope_result', 'testcase_scene_id')
        print('UpdateTestCase post:testcase_scene_id ', testcase_scene_id)
        id = request.args.get('id', id)
        print('UpdateTestCase: id', id)

        update_test_case_sql = 'update testcases set name=?,url=?,data=?,method=?,group_id=?,' \
                               'request_headers_id=?,regist_variable=?,regular=?,hope_result=? where id=?'
        cdb().opeat_db(update_test_case_sql, (name, url, data, method, group_id,
                                              request_headers_id, regist_variable, regular, hope_result,id))
        FrontLogs('编辑测试用例 name: %s 成功' % name).add_to_front_log()
        app.logger.info('message:update testcases success, name: %s' % name)
        print('UpdateTestCase post:testcase_scene_id return :', testcase_scene_id, len(testcase_scene_id))
        if testcase_scene_id not in(None, "None"):
            print('UpdateTestCase post:testcase_scene_id return :', testcase_scene_id is True,len(testcase_scene_id))
            return redirect(url_for('testcase_scene_blueprint.testcase_scene_testcase_list'))
        return redirect(url_for('testcase_blueprint.test_case_list'))


class DeleteTestCase(MethodView):

    def get(self, id=-1):
        testcase_scene_id = request.args.get('testcase_scene_id', None)
        delete_test_case_sql = 'delete from testcases where id=?'
        cdb().opeat_db(delete_test_case_sql, (id,))
        FrontLogs('删除测试用例 id: %s 成功' % id).add_to_front_log()
        app.logger.info('message:delete testcases success, id: %s' % id)
        if testcase_scene_id not in(None, "None"):
            return redirect(url_for('testcase_scene_blueprint.testcase_scene_testcase_list'))
        return redirect(url_for('testcase_blueprint.test_case_list'))


class ModelTestCase(MethodView):

    def get(self, id=-1):
        testcase = TestCases.query.get(id)
        if testcase.is_model == 0:
            testcase.is_model = 1
        else:
            testcase.is_model = 0
        db.session.commit()
        return redirect(url_for('testcase_blueprint.test_case_list'))


class TestCaseValidata(MethodView):

    def get(self):
        name = request.args.get('name')
        testcase = TestCases.query.filter(TestCases.name == name).count()
        if testcase != 0:
            return jsonify(False)
        else:
            return jsonify(True)


class TestCaseUpdateValidata(MethodView):

    def get(self):
        name = request.args.get('name')
        testcase_id = request.args.get('testcase_id')
        testcase = TestCases.query.filter(TestCases.id != testcase_id).filter(TestCases.name == name).count()
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


testcase_blueprint.add_url_rule('/testcasevalidate/', view_func=TestCaseValidata.as_view('testcase_validate'))
testcase_blueprint.add_url_rule('/testcaseupdatevalidate/', view_func=TestCaseUpdateValidata.as_view('testcase_update_validate'))
testcase_blueprint.add_url_rule('/test_case_hope_result_validate/', view_func=TestCaseHopeResultValidata.as_view('test_case_hope_result_validate'))
