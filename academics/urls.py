from django.urls import path
from . import views

app_name = 'academics'
urlpatterns = [
    path('timetable/', views.TimetableView.as_view(), name='timetable'),
    path('timetable/grid/', views.TimetableGridView.as_view(), name='timetable_grid'),
    path('timetable/create/', views.TimetableCreateView.as_view(), name='create_timetable'),
    path('timetable/<int:pk>/edit/', views.TimetableUpdateView.as_view(), name='edit_timetable'),
    path('lesson-notes/', views.LessonNotesView.as_view(), name='lesson_notes'),
    path('lesson-notes/create/', views.CreateLessonNoteView.as_view(), name='create_lesson_note'),
    path('class-results/', views.ClassResultsView.as_view(), name='class_results'),
]