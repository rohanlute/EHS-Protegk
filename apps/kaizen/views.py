from django.shortcuts import render, redirect
from django.views.generic import TemplateView, ListView, DeleteView, CreateView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from apps.accounts.models import *
from .models import *
from django.db.models import Count, Q
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
        category_counts = KaizenCategory.objects.aggregate(
            total_categories=Count('pk'),
            active_categories=Count('pk', filter=Q(is_active=True)),
            inactive_categories=Count('pk', filter=Q(is_active=False)),
        )
        context.update(category_counts)
        return context

class KaizenCategoryCreateView(LoginRequiredMixin, CreateView):
    model = KaizenCategory
    form_class = KaizenCategoryForm
    template_name = 'kaizen/category_form.html'
    success_url = reverse_lazy('kaizen:category_list')

    def form_valid(self, form):
        kaizen_category = form.save(commit=False)
        kaizen_category.created_by = self.request.user
        kaizen_category.save()

        messages.success(
            self.request, f'Kaizen Type "{kaizen_category.name}" created successfully!'
        )
        return super().form_valid(form)

class KaizenCategoryUpdateView(LoginRequiredMixin,UpdateView):
    model = KaizenCategory
    form_class = KaizenCategoryForm
    template_name = 'kaizen/category_form.html'
    success_url = reverse_lazy('kaizen:category_list')

    def form_valid(self, form):
        messages.success(
            self.request,
            f'Kaizen Category "{self.object.name}" updated successfully!'
        )
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['action'] = 'Update'
        context['kaizen_category'] = self.get_object

        return context

class KaizenCategoryDeleteView(LoginRequiredMixin, DeleteView):
    model = KaizenCategory
    template_name = 'kaizen/category_confirm_delete.html'
    success_url = reverse_lazy('kaizen:category_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['kaizen_category'] = self.object
        context['kaizen_count'] = 0
        return context

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        kaizen_category_name = self.object.name
        self.success_url = self.get_success_url()
        self.object.delete()
        messages.success(
            request, f'Kaizen Category "{kaizen_category_name}" deleted successfully!'
        )
        return redirect(self.success_url)   
class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'kaizen/dashboard.html'