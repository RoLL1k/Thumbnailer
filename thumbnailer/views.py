import os
from celery import current_app
from django import forms
from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import render
from django.utils.datastructures import MultiValueDictKeyError
from django.views import View
from .tasks import make_thumbnails


class FileUploadForm(forms.Form):
    image_file = forms.ImageField(required=True)


def get_thumbnails(request):
    thumbnails = []
    for opt_number in range(1, 6):
        try:
            size = int(request.POST[f'opt-{opt_number}'])
            thumbnails.append((size, size))
        except MultiValueDictKeyError:
            continue
    return thumbnails


class HomeView(View):
    template = 'thumbnailer/home.html'

    def get(self, request):
        form = FileUploadForm()
        return render(request, self.template, { 'form': form })

    def post(self, request):
        form = FileUploadForm(request.POST, request.FILES)
        context = {}
        if form.is_valid():
            file_path = os.path.join(settings.IMAGES_DIR, request.FILES['image_file'].name)
            with open(file_path, 'wb+') as fp:
                for chunk in request.FILES['image_file']:
                    fp.write(chunk)
            thumbnails = get_thumbnails(request)
            task = make_thumbnails.delay(file_path, thumbnails=thumbnails)
            context['task_id'] = task.id
            context['task_status'] = task.status
            return render(request, self.template, context)
        context['form'] = form
        return render(request, self.template, context)


class TaskView(View):
    def get(self, request, task_id):
        task = current_app.AsyncResult(task_id)
        response_data = {'task_status': task.status, 'task_id': task.id}
        if task.status == 'SUCCESS':
            response_data['results'] = task.get()
        return JsonResponse(response_data)
