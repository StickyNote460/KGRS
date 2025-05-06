from django.shortcuts import get_object_or_404, render
from .models import Course, User

# Create your views here.

def home(request):
    return render(request, 'recommender/home.html', {
        'courses': Course.objects.order_by('-id')[:5],
        'users': User.objects.order_by('-id')[:5]
    })

def course_detail(request, pk):
    course = get_object_or_404(
        Course.objects.prefetch_related('concepts__field'),
        pk=pk
    )
    return render(request, 'recommender/course_detail.html', {
        'course': course
    })

def user_profile(request, pk):
    user = get_object_or_404(
        User.objects.prefetch_related('courses__concepts'),
        pk=pk
    )
    return render(request, 'recommender/user_profile.html', {
        'user': user
    })


# recommender/views.py
from .recommendations.graph_based.path_finder import PathFinder

#5.2 20:24
def learning_path_view(request, course_id):
    user = request.user
    target_course = get_object_or_404(Course, id=course_id)
    recommender = PathFinder()
    path = recommender.recommend(user, target_course)

    return render(request, 'recommender/path.html', {
        'course': target_course,
        'path': Course.objects.filter(id__in=path)
    })