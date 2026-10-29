from django.shortcuts import render
from django.views.generic import TemplateView, ListView, DeleteView, CreateView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from apps.accounts.models import *
from .models import *
from django.db.models import Q
from .forms import *
from django.urls import reverse, reverse_lazy
from django.contrib import messages

class KaizenCategoryListView(LoginRequiredMixin, ListView):
    model = KaizenCategory
    template_name = 'kaizen/category_list.html'
    context_object_name = 'kaizen_category'
    paginate_by = 20

    def get_queryset(self):
        queryset = KaizenCategory.objects.order_by('name')
        search_query = self.request.GET.get('search','')
        if search_query:
            queryset = queryset.filter(
                Q(name__icontains=search_query) |
                Q(name__icontains=search_query) |
                Q(description__icontains=search_query)
            )
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context ['search_query'] = self.request.GET.get('search', '')
        return context

class KaizenCategoryCreateView(LoginRequiredMixin, CreateView):
    model = KaizenCategory
    form_class = KaizenCategoryForm
    template_name = 'kaizen/category_create.html'
    success_url = reverse_lazy('kaizen:category_list')

    def form_valid(self, form):
        kaizen_category = form.save(commit=False)
        kaizen_category.created_by = self.request.user
        kaizen_category.save()

        messages.success(
            self.request, f'Kaizen Type "{kaizen_category.name}" created successfully!'
        )
        return super().form_valid(form)
    
class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'kaizen/dashboard.html'