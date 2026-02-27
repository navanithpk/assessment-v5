from django.urls import path
from . import views
from . import google_oauth
from . import import_sessions_views
from . import analytics_views
from . import pdf_tasks_views
from . import answer_space_designer_views
from . import report_card_views
from . import bulk_import_views
from . import dlc_views
from . import qp_ms_ingester_views
from . import descriptive_pdf_slicer_views
from . import ai_tagging_views
from core import analytics_api
from . import resource_views

urlpatterns = [
    # Root
    path("", views.root_redirect, name="root"),
    path("admin/dashboard/", views.admin_dashboard, name="admin_dashboard"),

    # Auth
    path("accounts/login/", views.custom_login, name="login"),
    path("accounts/google/login/", google_oauth.get_google_auth_url, name="google_login"),
    path("accounts/google/callback/", google_oauth.google_auth_callback, name="google_callback"),

    # Dashboards
    path("teacher/", views.teacher_dashboard, name="teacher_dashboard"),
    path("teacher/academic-overview/", views.academic_overview_dashboard, name="academic_overview_dashboard"),
    path("student/dashboard/", views.student_dashboard, name="student_dashboard"),
    path("student/change-password/", views.student_change_password, name="student_change_password"),

    # User Management (NEW - Simplified)
    path("teacher/users/add/", views.add_user, name="add_user"),
    path("teacher/users/manage/", views.manage_users, name="manage_users"),
    path("teacher/users/change-password/", views.change_password, name="change_password"),

    # Tests (teacher)
    path("teacher/tests/", views.tests_list, name="tests_list"),
    path("teacher/tests/create/", views.create_test, name="create_test"),
    path("teacher/tests/create-descriptive/", views.create_descriptive_test, name="create_descriptive_test"),
    path("teacher/tests/<int:test_id>/edit-descriptive/", views.edit_descriptive_test, name="edit_descriptive_test"),
    path("teacher/tests/<int:test_id>/edit/", views.test_editor, name="edit_test"),
    path("teacher/tests/<int:test_id>/delete/", views.delete_test, name="delete_test"),
    path("teacher/tests/<int:test_id>/toggle/", views.toggle_publish, name="toggle_publish"),
    path("teacher/tests/<int:test_id>/duplicate/", views.duplicate_test, name="duplicate_test"),
    path("teacher/tests/<int:test_id>/autosave/", views.autosave_test, name="autosave_test"),
    path("teacher/tests/<int:test_id>/add-questions/", views.add_questions_to_test, name="add_questions_to_test"),
    path("teacher/tests/<int:test_id>/questions/<int:test_question_id>/remove/", 
         views.remove_question_from_test, name="remove_question_from_test"),
    path("teacher/tests/<int:test_id>/inline-add-question/",
         views.inline_add_question, name="inline_add_question"),
    
    # Tests (student)
    path("student/tests/", views.student_tests_list, name="student_tests_list"),

    # Questions
    path("questions/", views.question_library, name="question_library"),
    path("questions/add/", views.add_edit_question, name="add_question"),
    path("questions/edit/<int:question_id>/", views.add_edit_question, name="edit_question"),
    path("questions/<int:question_id>/edit-v2/", views.edit_question_v2, name="edit_question_v2"),
    path("questions/<int:question_id>/edit-spaces/", views.edit_structured_question, name="edit_structured_question"),
    path("questions/delete/<int:question_id>/", views.delete_question, name="delete_question"),
    path("questions/import-mcq-images/", views.import_mcq_images, name="import_mcq_images"),
    path("questions/import-mcq-pdf/", views.import_mcq_pdf, name="import_mcq_pdf"),
    path("questions/qp-slicer/", views.qp_slicer_workstation, name="qp_slicer_workstation"),
    path("questions/import-qp-slices/", views.import_qp_slices, name="import_qp_slices"),
    path("questions/descriptive-pdf-slicer/", descriptive_pdf_slicer_views.descriptive_pdf_slicer, name="descriptive_pdf_slicer"),
    path("questions/qp-ms-ingester/", qp_ms_ingester_views.qp_ms_ingester, name="qp_ms_ingester"),
    path("questions/qp-ms-ingester/save/", qp_ms_ingester_views.qp_ms_ingester_save, name="qp_ms_ingester_save"),
    path("questions/qp-ms-ingester/update-tree/", qp_ms_ingester_views.qp_ms_ingester_update_tree, name="qp_ms_ingester_update_tree"),
    path("questions/<int:pk>/exists/", views.question_exists),

    # Question Library API (for test editors)
    path("questions/api/search/", views.question_library_api_search, name="question_library_api_search"),
    path("questions/api/<int:question_id>/", views.question_library_api_get, name="question_library_api_get"),
    path("questions/api/create/", views.question_library_api_create, name="question_library_api_create"),
    path("questions/add-structured/", views.structured_question_editor, name="structured_question_editor"),


    # Answer Space Designer (Step 2 of two-step non-MCQ import)
    path("questions/configure-answer-spaces/", answer_space_designer_views.list_unconfigured_questions, name="unconfigured_questions_list"),
    path("questions/<int:question_id>/answer-spaces/", answer_space_designer_views.answer_space_designer, name="answer_space_designer"),
    path("questions/<int:question_id>/answer-spaces/save/", answer_space_designer_views.save_answer_spaces, name="save_answer_spaces"),
    path("questions/<int:question_id>/answer-spaces/duplicate/", answer_space_designer_views.duplicate_part_config, name="duplicate_part_config"),

    # PDF Import Sessions
    path("teacher/import-sessions/", import_sessions_views.pending_import_sessions, name="pending_import_sessions"),
    path("teacher/import-sessions/save/", import_sessions_views.save_import_session, name="save_import_session"),
    path("teacher/import-sessions/<int:session_id>/resume/", import_sessions_views.resume_import_session, name="resume_import_session"),
    path("teacher/import-sessions/<int:session_id>/delete/", import_sessions_views.delete_import_session, name="delete_import_session"),
    path("teacher/import-sessions/<int:session_id>/complete/", import_sessions_views.mark_session_complete, name="mark_session_complete"),

    # PDF Task Management
    path("teacher/pdf-tasks/", pdf_tasks_views.pdf_tasks_list, name="pdf_tasks_list"),
    path("teacher/pdf-tasks/check-duplicate/", pdf_tasks_views.check_duplicate_pdf, name="check_duplicate_pdf"),
    path("teacher/pdf-tasks/mark-processed/", pdf_tasks_views.mark_pdf_processed, name="mark_pdf_processed"),
    path("teacher/pdf-tasks/<int:session_id>/delete/", pdf_tasks_views.delete_task, name="delete_task"),
    path("teacher/pdf-tasks/<int:session_id>/complete/", pdf_tasks_views.mark_task_complete, name="mark_task_complete"),
    path("teacher/pdf-tasks/<int:session_id>/pause/", pdf_tasks_views.pause_task, name="pause_task"),
    path("teacher/pdf-tasks/<int:session_id>/resume/", pdf_tasks_views.resume_task, name="resume_task"),

    # AJAX
    path("ajax/topics/", views.ajax_topics, name="ajax_topics"),
    path("ajax/los/", views.ajax_learning_objectives, name="ajax_los"),
    path("ajax/ai-suggest-topic/", views.ai_suggest_topic, name="ai_suggest_topic"),
    path("ajax/ai-suggest-los/", views.ai_suggest_learning_objectives, name="ai_suggest_los"),

    # Bulk AI tagging
    path("teacher/bulk-ai-tag/", views.bulk_ai_tag_questions, name="bulk_ai_tag"),
    path("teacher/ai-logs/", views.ai_tagging_logs, name="ai_tagging_logs"),
    path("teacher/ai-logs/view/<str:filename>/", views.view_log_file, name="view_log_file"),

    # Untagged Questions & Background Tagging
    path("teacher/untagged-questions/", views.untagged_questions_view, name="untagged_questions"),
    path("teacher/ai-tag-untagged/", views.start_background_tagging, name="start_background_tagging"),
    path("teacher/ai-tag-progress/<str:task_id>/", views.get_tagging_progress, name="get_tagging_progress"),

    # Students (Legacy - keep for compatibility)
    path("teacher/students/", views.students_list, name="students_list"),
    path("teacher/students/add/", views.add_student, name="add_student"),
    path("teacher/students/<int:student_id>/edit/", views.edit_student, name="edit_student"),
    
    # Groups
    path("teacher/groups/", views.groups_list, name="groups_list"),
    path("teacher/groups/add/", views.add_group, name="add_group"),
    #path("teacher/groups/<int:group_id>/edit/", views.edit_group, name="edit_group"),
    #path("teacher/groups/<int:group_id>/delete/", views.delete_group, name="delete_group"),
    
    # Performance
    path("teacher/performance/class/", views.class_performance, name="class_performance"),
    path("teacher/users/add/", views.add_user, name="add_user"),
    path("teacher/groups/", views.groups_list, name="groups_list"),
    path("teacher/class-groups/", views.manage_class_groups, name="manage_class_groups"),
    path("teacher/class-groups/<int:group_id>/students/", views.get_group_students, name="get_group_students"),     
    path("teacher/users/manage/", views.manage_users, name="manage_users"),
    
    
    path("teacher/groups/", views.groups_list, name="groups_list"),

    # Student Test Taking
    path("student/tests/<int:test_id>/take/", views.take_test, name="take_test"),
    path("student/tests/<int:test_id>/autosave/", views.autosave_test_answers, name="autosave_test_answers"),
    path("student/tests/<int:test_id>/answers/", views.get_saved_answers, name="get_saved_answers"),
    path("student/tests/<int:test_id>/submit/", views.submit_test, name="submit_test"),

    # Student Results
    path("student/results/", views.student_results, name="student_results"),
    path("student/tests/<int:test_id>/review/", views.student_test_review, name="student_test_review"),
    path("student/practice/<int:topic_id>/", views.student_practice, name="student_practice"),

    # Resources (shared between teachers & students)
    path("resources/", resource_views.resource_list, name="resource_list"),
    path("resources/upload/", resource_views.resource_upload, name="resource_upload"),
    path("resources/<int:resource_id>/delete/", resource_views.resource_delete, name="resource_delete"),

    # Analytics
    path("student/analytics/", analytics_views.student_analytics_dashboard, name="student_analytics"),
    #path("teacher/analytics/", analytics_views.teacher_analytics_dashboard, name="teacher_analytics"),
    #path("teacher/tests/<int:test_id>/analytics/", analytics_views.test_analytics, name="test_analytics"),
    # Examiner report API (JSON)
    path(
        "teacher/tests/<int:test_id>/mcq-examiner-report/",
        analytics_views.mcq_examiner_report,
        name="mcq_examiner_report",
    ),
    path('teacher/tests/<int:test_id>/analytics/', 
         views.test_analytics_view, 
         name='test_analytics'),

    # Test Monitoring & Grading
    path("teacher/tests/<int:test_id>/monitor/", views.monitor_test, name="monitor_test"),
    path("teacher/tests/<int:test_id>/monitor/api/", views.monitor_test_api, name="monitor_test_api"),
    path("teacher/tests/<int:test_id>/grade/", views.grade_test_spreadsheet, name="grade_test_answers"),
    path("teacher/tests/<int:test_id>/grade-old/", views.grade_test_answers, name="grade_test_answers_old"),
    path("teacher/tests/<int:test_id>/save-grade/", views.save_grade, name="save_grade"),
    path("teacher/grading/save/", views.save_grade, name="save_grade_legacy"),
    path("teacher/grading/save-space-grade/", views.save_answer_space_grade, name="save_answer_space_grade"),
    path("teacher/grading/ai-grade/", views.ai_grade_answer, name="ai_grade_answer"),
    path("teacher/tests/<int:test_id>/publish-results/", views.publish_results, name="publish_results"),
    

    path("teacher/tests/<int:test_id>/analytics/questions/", analytics_api.question_analytics),
    path("teacher/tests/<int:test_id>/analytics/lo-heatmap/", analytics_api.lo_mastery_heatmap),

    # Report Cards
    path("teacher/report-cards/", report_card_views.report_card_dashboard, name="report_card_dashboard"),
    path("teacher/report-cards/<int:student_id>/data/", report_card_views.report_card_detail, name="report_card_detail"),
    path("teacher/report-cards/reissue-suggestions/", report_card_views.topic_reissue_suggestions, name="topic_reissue_suggestions"),
    path("teacher/reissue-dashboard/", report_card_views.reissue_dashboard, name="reissue_dashboard"),
    path("teacher/assign-practice/", report_card_views.assign_practice, name="assign_practice"),

    # Smart Test Generator
    path("teacher/smart-test/", report_card_views.smart_test_generator, name="smart_test_generator"),
    path("teacher/smart-test/analyse/", report_card_views.smart_test_analyse, name="smart_test_analyse"),
    path("teacher/smart-test/create/", report_card_views.smart_test_create, name="smart_test_create"),
    path("teacher/tests/<int:test_id>/analytics/risk/", analytics_api.risk_prediction),
    path("teacher/tests/<int:test_id>/analytics/summary/", analytics_api.lmstudio_summary),

    # AI Tagging Export/Import
    path("teacher/ai-tagging/export/", ai_tagging_views.ai_tagging_export, name="ai_tagging_export"),
    path("teacher/ai-tagging/export-text/", ai_tagging_views.ai_tagging_export_text, name="ai_tagging_export_text"),
    path("teacher/ai-tagging/import/", ai_tagging_views.ai_tagging_import, name="ai_tagging_import"),

    # Bulk Import
    path("teacher/users/bulk-import/", bulk_import_views.bulk_import_users, name="bulk_import_users"),
    path("teacher/users/download-template/", bulk_import_views.download_user_template, name="download_user_template"),
    path("teacher/users/download-student-template/", bulk_import_views.download_student_template, name="download_student_template"),
    path("teacher/users/download-teacher-template/", bulk_import_views.download_teacher_template, name="download_teacher_template"),

    # School Settings
    path("teacher/school-settings/", views.edit_school_settings, name="edit_school_settings"),

    # Teacher Assignment API
    path("teacher/tests/assign-teachers/", views.assign_teachers_to_test, name="assign_teachers_to_test"),
    path("teacher/tests/<int:test_id>/teachers/", views.get_test_teachers, name="get_test_teachers"),

    # DLC Management
    path("teacher/dlc/", dlc_views.dlc_dashboard, name="dlc_dashboard"),
    path("teacher/dlc/<int:bank_id>/activate/", dlc_views.activate_dlc, name="activate_dlc"),
    path("teacher/dlc/<int:bank_id>/deactivate/", dlc_views.deactivate_dlc, name="deactivate_dlc"),
    path("teacher/dlc/create/", dlc_views.create_dlc, name="create_dlc"),
    path("teacher/subject-grade-combinations/", dlc_views.subject_grade_combinations, name="subject_grade_combinations"),
    path("teacher/subject-grade-combinations/add/", dlc_views.add_combination, name="add_combination"),

]