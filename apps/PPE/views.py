from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import render, redirect,get_object_or_404
from django.http import JsonResponse
from apps.accounts.models import User
from django.db.models import Count, Q
from .models import PPESizeQuantity
from itertools import zip_longest
from .models import *
from .forms import *
from django.core.paginator import EmptyPage, Paginator
from django.db.models import Sum
from datetime import date
# Create your views here.

@login_required
def category_create(request):
    """Create new PPE Category"""
    if request.method == 'POST':
        form = PPECategoryForm(request.POST)
        if form.is_valid():
            category = form.save(commit=False)
            category.created_by = request.user
            category.save()
            messages.success(request, f'Category "{category.category_name}" created successfully!')
            return redirect('PPE:category_list')
    else:
        form = PPECategoryForm()
    context = {
        'form': form,
        'action': 'Create',
        'title': 'Create New Category'
    }
    return render(request, 'PPE/configuration/category_form.html', context)
@login_required
def category_edit(request, pk):
    """Edit existing category"""
    category = get_object_or_404(PPECategory, pk=pk)
    if request.method == 'POST':
        form = PPECategoryForm(request.POST, instance=category)
        if form.is_valid():
            form.save()
            messages.success(request, f'Category "{category.category_name}" updated successfully!')
            return redirect('PPE:category_list')
    else:
        form = PPECategoryForm(instance=category)
    context = {
        'form': form,
        'action': 'Edit',
        'title': f'Edit Category: {category.category_name}',
        'category': category
    }
    return render(request, 'PPE/configuration/category_form.html', context)

@login_required
def category_list(request):
    """List all Categories List"""
    categories = PPECategory.objects.order_by('category_name')
    # Filter
    search = request.GET.get('search')
    if search:
        categories = categories.filter(
            Q(category_name__icontains=search) |
            Q(category_code__icontains=search) |
            Q(description__icontains=search)
            
        )
    # Pagination
    paginator = Paginator(categories, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search': search
    }
    return render(request, 'PPE/configuration/category_list.html', context)

@login_required
def category_delete(request, pk):
    """Permanently delete category"""
    category = get_object_or_404(PPECategory, pk=pk)
    
    if request.method == 'POST':
        category.delete()
        messages.success(request, f'Category "{category.category_name}" deleted successfully!')
        return redirect('PPE:category_list')
    
    context = {
        'category': category
    }
    return render(request, 'PPE/configuration/category_confirm_delete.html', context)
@login_required
def master_list(request):
    """list all ppe master"""
    ppe_list = PPEItem.objects.all()
    query = request.GET.get('search')
    if query:
        ppe_list = ppe_list.filter(
            Q(name__icontains=query) |
            Q(category__category_name__icontains=query)|
            Q(ppe_code__icontains=query)
        )
    context = {
        "ppe_list": ppe_list
    }
    paginator = Paginator(ppe_list, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render(
        request,
        'PPE/configuration/master_list.html',
        {
            'page_obj': page_obj
        }
    )
@login_required
def create_ppe(request):
    if request.method == 'POST':
        form = PPEItemForm(request.POST)
        if form.is_valid():
            ppe = form.save(commit=False)
            ppe.is_active = request.POST.get('is_active') == 'on'
            # Save PPE
            ppe.save()
            sizes = request.POST.getlist('size[]')
            for size in sizes:
                if size and size.strip():
                    PPESizeQuantity.objects.create(
                        ppe_item=ppe,
                        size=size.strip()
                    )
            messages.success(
                request,
                f'PPE "{ppe.name}" created successfully!'
            )
            return redirect('PPE:master_list')
        messages.error(request, "Please correct the errors below.")
    else:
        form = PPEItemForm()
    context = {
        'form': form,
        'categories': PPECategory.objects.filter(is_active=True),
        'ppe_code': PPEItem.generate_ppe_code(),  # FIXED (classmethod)
        'action': 'Create',
        'title': 'Create PPE Item'
    }
    return render(request, 'PPE/configuration/create_ppe.html', context)
@login_required
def ppe_detail(request, pk):
    ppe = get_object_or_404(PPEItem, pk=pk)
    size_quantities = PPESizeQuantity.objects.filter(ppe_item=ppe)
    context = {
        'ppe': ppe,
        'size_quantities': size_quantities,
    }
    return render(request, 'PPE/configuration/ppe_detail.html', context)
@login_required
def ppe_delete(request, pk):
    ppe = get_object_or_404(PPEItem, pk=pk)
    if request.method == "POST":
        ppe_name = ppe.name
        ppe.delete()
        messages.success(request, f'PPE Item "{ppe_name}" deleted successfully!')
        return redirect('PPE:master_list')
    return render(request, 'PPE/configuration/ppe_delete.html', {
        'ppe': ppe
    })
@login_required
def master_edit(request, pk):
    ppe = get_object_or_404(PPEItem, pk=pk)
    if request.method == 'POST':
        form = PPEItemForm(request.POST, instance=ppe)
        if form.is_valid():
            ppe = form.save()
            #delete existing size
            ppe.size_quantities.all().delete()
            # Save updated sizes
            sizes = request.POST.getlist('size[]')
            for size in sizes:
                if size.strip():
                    PPESizeQuantity.objects.create(
                        ppe_item=ppe,
                        size=size.strip()
                    )
            messages.success(request, "PPE updated successfully!")
            return redirect('PPE:master_list')
    return render(
        request,
        'PPE/configuration/create_ppe.html',
        {
            'ppe': ppe,
            'categories': PPECategory.objects.filter(is_active=True),
            'existing_sizes': ppe.size_quantities.all(),
            'action': 'Edit'
        }
    )
@login_required
def stock_list(request):
    stocks = PPEStockTransaction.objects.select_related(
        'ppe_item',
        'ppe_item__category'
    ).order_by('-created_at')
    return render(request, 'ppe/configuration/stock_list.html', {
        'stocks': stocks
    })
@login_required
def stock_create(request):
    form = PPEStockTransactionForm(request.POST or None)
    selected_item = None
    sizes = []
    category = ""
    ppe_item_id = request.GET.get('ppe_item')
    if ppe_item_id:
        try:
            selected_item = PPEItem.objects.get(id=ppe_item_id)
            sizes = PPESizeQuantity.objects.filter(
                ppe_item=selected_item
            )
            category = selected_item.category.category_name
        except PPEItem.DoesNotExist:
            selected_item = None
    if request.method == "POST":
        ppe_item_id = request.POST.get('ppe_item')
        transaction_type = request.POST.get('transaction_type')
        unit = request.POST.get('unit')
        transaction_date = request.POST.get('transaction_date')
        reference_number = request.POST.get('reference_number')
        remarks = request.POST.get('remarks')
        size_ids = request.POST.getlist('size_id[]')
        qtys = request.POST.getlist('qty[]')
        if not ppe_item_id:
            messages.error(
                request,
                "Please select PPE Item."
            )
            return redirect('PPE:stock_create')
        ppe_item = PPEItem.objects.get(id=ppe_item_id)
        size_quantities = {}
        total = 0
        for size_id, qty in zip(size_ids, qtys):
            try:
                qty = int(qty or 0)
            except ValueError:
                qty = 0
            if qty > 0:
                size_obj = PPESizeQuantity.objects.get(
                    id=size_id
                )
                # ADD STOCK TO SIZE TABLE
                size_obj.available_quantity += qty
                size_obj.save()
                size_quantities[size_obj.size] = qty
                total += qty
        if total <= 0:
            return render(
                request,
                'ppe/configuration/stock_form.html',
                {
                    'form': form,
                    'selected_item': selected_item,
                    'sizes': sizes,
                    'category': category,
                    'today': timezone.now().date(),
                    'action': 'Create',
                    'error': 'Please enter quantity.'
                }
            )
        PPEStockTransaction.objects.create(
            ppe_item=ppe_item,
            size_quantities=size_quantities,
            quantity=total,
            total=total,
            transaction_type=transaction_type,
            unit=unit,
            transaction_date=transaction_date,
            reference_number=reference_number,
            remarks=remarks,
            created_by=request.user,
            is_active=True
        )
        messages.success(
            request,
            "Stock saved successfully."
        )
        return redirect('PPE:stock_list')
    return render(
        request,
        'ppe/configuration/stock_form.html',
        {
            'form': form,
            'selected_item': selected_item,
            'sizes': sizes,
            'category': category,
            'today': timezone.now().date(),
            'action': 'Create'
        }
    )
@login_required
def stock_edit(request, pk):
    stock = get_object_or_404(PPEStockTransaction, pk=pk)
    selected_item = stock.ppe_item
    sizes = PPESizeQuantity.objects.filter(ppe_item=selected_item)
    category = selected_item.category.category_name
    if request.method == "POST":
        ppe_item_id = request.POST.get('ppe_item')
        transaction_type = request.POST.get('transaction_type')
        unit = request.POST.get('unit')
        transaction_date = request.POST.get('transaction_date')
        reference_number = request.POST.get('reference_number')
        remarks = request.POST.get('remarks')
        is_active = request.POST.get('is_active') == 'on'
        size_ids = request.POST.getlist('size_id[]')
        qtys = request.POST.getlist('qty[]')
        selected_item = PPEItem.objects.get(id=ppe_item_id)
        size_map = {
            str(s.id): s.size
            for s in PPESizeQuantity.objects.filter(id__in=size_ids)
        }
        size_quantities = {}
        total = 0
        for size_id, qty in zip(size_ids, qtys):
            try:
                quantity = int(qty or 0)
            except ValueError:
                quantity = 0

            if quantity > 0:
                size_name = size_map.get(str(size_id))
                if size_name:
                    size_quantities[size_name] = quantity
                    total += quantity
        if total <= 0:
            messages.error(request, "Quantity required")
            return render(request, 'ppe/configuration/stock_form.html', {
                'form': PPEStockTransactionForm(instance=stock),
                'stock': stock,
                'selected_item': selected_item,
                'sizes': sizes,
                'category': category,
                'action': 'Edit'
            })
        stock.ppe_item = selected_item
        stock.transaction_type = transaction_type
        stock.unit = unit
        stock.transaction_date = transaction_date
        stock.reference_number = reference_number
        stock.remarks = remarks
        stock.is_active = is_active
        stock.size_quantities = size_quantities
        stock.total = total
        stock.quantity = total
        stock.updated_by = request.user
        stock.save()
        return redirect('PPE:stock_list')
    saved_quantities = stock.size_quantities or {}
    for s in sizes:
        s.stock_quantity = saved_quantities.get(s.size, 0)
    return render(request, 'ppe/configuration/stock_form.html', {
        'form': PPEStockTransactionForm(instance=stock),
        'stock': stock,
        'selected_item': selected_item,
        'sizes': sizes,
        'category': category,
        'transaction_date': stock.transaction_date,
        'action': 'Edit'
    })
@login_required
def stock_detail(request, pk):
    stock = get_object_or_404(PPEStockTransaction, pk=pk)
    saved_quantities = stock.size_quantities or {}
    return render(request, 'ppe/configuration/stock_detail.html', {
        'stock': stock,
        'saved_quantities': saved_quantities
    })
@login_required
def stock_delete(request, pk):
    stock = get_object_or_404(PPEStockTransaction, pk=pk)
    if request.method == "POST":
        stock.delete()
        messages.success(request, "Stock deleted successfully")
        return redirect('PPE:stock_list')
    return render(request, 'ppe/configuration/stock_delete.html', {
        'stock': stock
    })

@login_required
def IssueManagement_list(request):
    search = request.GET.get('search', '')
    from django.db.models import Min
    issues = (PPEIssueManagement.objects.values('issue_group_no','issue_date','ppe_item__name')
        .annotate(
            total_persons=Count('id'),
            total_qty=Sum('quantity_issue'),
            first_id=Min('id')
        )
        .order_by('-issue_group_no')
    )
    if search:
     issues = issues.filter(
        Q(issue_no__icontains=search) |
        Q(issue_to__icontains=search) |
        Q(issue_date__icontains=search) |
        Q(ppe_item__name__icontains=search) |
        Q(contractor_name__icontains=search) |
        Q(remarks__icontains=search) 
    ).distinct()
    paginator = Paginator(issues, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    context = {
        'page_obj': page_obj,
        'search': search,
    }
    return render(
        request,
        'ppe/Management/IssueManagement_list.html',
        context
    )
@login_required
def IssueManagement_create(request):

    selected_item = None
    available_quantity = 0
    sizes = []

    ppe_item_id = request.GET.get('ppe_item')

    employees = User.objects.filter(
        is_active=True
    ).select_related(
        'department'
    )

    if ppe_item_id:

        selected_item = PPEItem.objects.get(
            id=ppe_item_id
        )

        available_quantity = (
            PPESizeQuantity.objects.filter(
                ppe_item=selected_item
            ).aggregate(
                total_stock=Sum(
                    'available_quantity'
                )
            )['total_stock'] or 0
        )

        sizes = PPESizeQuantity.objects.filter(
            ppe_item=selected_item
        )

    if request.method == 'POST':

        issue_date = request.POST.get(
            'issue_date'
        )

        ppe_item_id = request.POST.get(
            'ppe_item'
        )

        if not ppe_item_id:

            messages.error(
                request,
                "Please select PPE Item."
            )

            return redirect(
                request.path
            )

        ppe_item = PPEItem.objects.get(
            id=ppe_item_id
        )

        issue_to_list = request.POST.getlist(
            'issue_to[]'
        )

        employee_list = request.POST.getlist(
            'employee[]'
        )

        contractor_list = request.POST.getlist(
            'contractor_name[]'
        )

        department_list = request.POST.getlist(
            'department[]'
        )

        contractor_department_list = request.POST.getlist(
            'contractor_department[]'
        )

        size_list = request.POST.getlist(
            'size[]'
        )

        qty_list = request.POST.getlist(
            'quantity_issue[]'
        )

        remarks_list = request.POST.getlist(
            'remarks[]'
        )

        # Generate ONE issue number
        issue_no = PPEIssueManagement.generate_issue_no()

        created_issues = []

        for (
            issue_to,
            employee_id,
            contractor_name,
            department_id,
            contractor_department,
            size_id,
            qty,
            remarks

        ) in zip_longest(

            issue_to_list,
            employee_list,
            contractor_list,
            department_list,
            contractor_department_list,
            size_list,
            qty_list,
            remarks_list

        ):

            if not size_id or not qty:
                continue

            qty = int(qty)

            selected_size = PPESizeQuantity.objects.get(
                id=size_id
            )

            if qty > selected_size.available_quantity:

                messages.error(
                    request,
                    f"{selected_size.size} has only "
                    f"{selected_size.available_quantity} quantity available."
                )

                return redirect(
                    request.path +
                    f'?ppe_item={ppe_item.id}'
                )

            employee = None

            if employee_id:

                employee = User.objects.get(
                    id=employee_id
                )

            issue = PPEIssueManagement.objects.create(

                issue_no=issue_no,

                issue_date=issue_date,

                ppe_item=ppe_item,

                available_quantity=
                    selected_size.available_quantity,

                issue_to=issue_to,

                employee=employee,

                contractor_name=
                    contractor_name,
                
                contractor_department=contractor_department,

                department_id=
                    department_id
                    if department_id
                    else None,

                size=selected_size,

                quantity_issue=qty,

                remarks=remarks,

                created_by=request.user

            )

            created_issues.append(
                issue
            )

            # Reduce stock

            selected_size.available_quantity -= qty

            selected_size.save()

            # Calculate total balance

            updated_total_stock = (
                PPESizeQuantity.objects.filter(
                    ppe_item=ppe_item
                ).aggregate(
                    total_stock=Sum(
                        'available_quantity'
                    )
                )['total_stock'] or 0
            )

            # Transaction Log

            PPEStockTransaction.objects.create(

                ppe_item=ppe_item,

                size=selected_size,

                transaction_type='ISSUE',

                quantity=qty,

                total=updated_total_stock,

                transaction_date=issue_date,

                reference_number=issue_no,

                remarks=remarks,

                created_by=request.user,

                is_active=True

            )

        messages.success(
            request,
            f"PPE Issue {issue_no} Created Successfully."
        )

        return redirect(
            'PPE:IssueManagement_list'
        )

    form = PPEIssueManagementForm()

    context = {

        'form': form,

        'selected_item': selected_item,

        'available_quantity':
            available_quantity,

        'sizes': sizes,

        'employees': employees,

    }

    return render(
        request,
        'ppe/Management/IssueManagement_create.html',
        context
    )
@login_required
def get_employee_department(request):
    employee_id = request.GET.get(
        'employee_id'
    )
    try:
        employee = User.objects.select_related(
            'department'
        ).get(
            id=employee_id
        )
        return JsonResponse({
            'department':
            employee.department.name
            if employee.department
            else ''
        })
    except User.DoesNotExist:
        return JsonResponse({
            'department': ''
        })

@login_required
def edit_issue(request, pk):

    current_record = get_object_or_404(
        PPEIssueManagement,
        pk=pk
    )

    issue_rows = PPEIssueManagement.objects.filter(
        issue_no=current_record.issue_no
    )

    employees = User.objects.filter(
        is_active=True
    ).select_related(
        'department'
    )

    sizes = PPESizeQuantity.objects.filter(
        ppe_item=current_record.ppe_item
    )

    available_quantity = (
        PPESizeQuantity.objects.filter(
            ppe_item=current_record.ppe_item
        ).aggregate(
            total_stock=Sum('available_quantity')
        )['total_stock'] or 0
    )

    if request.method == "POST":

        # Restore previous stock
        for row in issue_rows:

            size = row.size

            size.available_quantity += (
                row.quantity_issue
            )

            size.save()

        issue_rows.delete()

        issue_date = request.POST.get(
            'issue_date'
        )

        ppe_item = PPEItem.objects.get(
            id=request.POST.get(
                'ppe_item'
            )
        )

        issue_to_list = request.POST.getlist(
            'issue_to[]'
        )

        employee_list = request.POST.getlist(
            'employee[]'
        )

        contractor_list = request.POST.getlist(
            'contractor_name[]'
        )

        department_list = request.POST.getlist(
            'department[]'
        )

        size_list = request.POST.getlist(
            'size[]'
        )

        qty_list = request.POST.getlist(
            'quantity_issue[]'
        )

        remarks_list = request.POST.getlist(
            'remarks[]'
        )

        for i in range(len(size_list)):

            size_obj = PPESizeQuantity.objects.get(
                id=size_list[i]
            )

            qty = int(
                qty_list[i]
            )

            if qty > size_obj.available_quantity:

                messages.error(
                    request,
                    f"{size_obj.size} has only "
                    f"{size_obj.available_quantity} quantity available."
                )

                return redirect(
                    'PPE:edit_issue',
                    pk=current_record.id
                )

            PPEIssueManagement.objects.create(

                issue_no=current_record.issue_no,

                issue_date=issue_date,

                ppe_item=ppe_item,

                available_quantity=
                    size_obj.available_quantity,

                issue_to=issue_to_list[i],

                employee_id=
                    employee_list[i]
                    if employee_list[i]
                    else None,

                contractor_name=
                    contractor_list[i],

                department_id=
                    department_list[i]
                    if department_list[i]
                    else None,

                size=size_obj,

                quantity_issue=qty,

                remarks=remarks_list[i],

                created_by=request.user

            )

            size_obj.available_quantity -= qty
            size_obj.save()

        messages.success(
            request,
            "Issue Updated Successfully."
        )

        return redirect(
            'PPE:IssueManagement_list'
        )
    form = PPEIssueManagementForm()
    context = {
        'form' :form,
        'issue': current_record,

        'issue_rows': issue_rows,

        'employees': employees,

        'sizes': sizes,

        'selected_item':
            current_record.ppe_item,

        'available_quantity':
            available_quantity,

    }

    return render(request,
        'ppe/Management/IssueManagement_create.html',
        context
    )



@login_required
def issue_detail(request, pk):

    first_issue = get_object_or_404(PPEIssueManagement,pk=pk)

    issues = PPEIssueManagement.objects.filter(issue_group_no=first_issue.issue_group_no).select_related(
        'employee','department','size').order_by('id')

    available_quantity = (
        PPEStockTransaction.objects.filter(
            ppe_item=first_issue.ppe_item
        ).aggregate(
            total_stock=Sum('total')
        )['total_stock'] or 0
    )

    sizes = PPESizeQuantity.objects.filter(
        ppe_item=first_issue.ppe_item
    )

    context = {
        'issue': first_issue,
        'issues': issues,
        'available_quantity': available_quantity,
        'sizes': sizes,
    }

    return render(request,
        'ppe/Management/issue_detail.html',context
    )


@login_required
def issue_delete(request, pk):

    issue = get_object_or_404(PPEIssueManagement,pk=pk)

    if request.method == "POST":
        size_obj = issue.size

        size_obj.available_quantity += (issue.quantity_issue)

        size_obj.save()

        issue.delete()

        messages.success(
            request,
            "Issue deleted successfully"
        )

        return redirect(
            'PPE:IssueManagement_list'
        )

    return render(
        request,
        'ppe/management/issue_delete.html',
        {
            'issue': issue
        }
    )