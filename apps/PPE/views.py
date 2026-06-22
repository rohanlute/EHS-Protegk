from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import render, redirect,get_object_or_404
from django.http import JsonResponse
from apps.accounts.models import User
from apps.organizations.models import Plant
from django.db.models import Count, Q
from datetime import datetime
from .models import PPESizeQuantity
from itertools import zip_longest
from .models import *
from django.db.models import Min,Max,F
from django.db.models import Q
from .forms import *
from django.db.models import Sum
from .models import PPEReturnManagement
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
    ppe_list = PPEItem.objects.all()
    query = request.GET.get('search')
    if query:
        ppe_list = ppe_list.filter(
            Q(name__icontains=query) |
            Q(category__category_name__icontains=query) |
            Q(ppe_code__icontains=query)
        )
    paginator = Paginator(ppe_list, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render(
        request,
        'PPE/configuration/master_list.html',
        {
            'page_obj': page_obj,
            'search': query,
        }
    )
@login_required
def master_edit(request, pk):
    ppe = get_object_or_404(PPEItem, pk=pk)
    if request.method == 'POST':
        form = PPEItemForm(
            request.POST,
            instance=ppe
        )
        if form.is_valid():
            ppe = form.save(commit=False)
            ppe.is_active = (
                request.POST.get('is_active') == 'on'
            )
            ppe.save()
            submitted_sizes = {
                size.strip()
                for size in request.POST.getlist('size[]')
                if size.strip()
            }
            existing_sizes = {
                obj.size: obj
                for obj in ppe.sizes.all()
            }
            # Prevent deleting issued sizes
            for size_name, size_obj in existing_sizes.items():
                if size_name not in submitted_sizes:
                    if PPEIssueManagement.objects.filter(
                        size=size_obj
                    ).exists():
                        messages.error(
                            request,
                            f"Size '{size_name}' has already been issued and cannot be removed."
                        )
                        return redirect(
                            'PPE:master_edit',
                            pk=ppe.pk
                        )
            # Add new sizes
            for size_name in submitted_sizes:
                if size_name not in existing_sizes:
                    PPESizeQuantity.objects.create(
                        ppe_item=ppe,
                        size=size_name
                    )
            # Delete removed sizes
            for size_name, size_obj in existing_sizes.items():
                if size_name not in submitted_sizes:
                    size_obj.delete()
            messages.success(
                request,
                "PPE updated successfully!"
            )
            return redirect('PPE:master_list')
        messages.error(
            request,
            "Please correct the errors below."
        )
    else:
        form = PPEItemForm(instance=ppe)
    return render(
        request,
        'PPE/configuration/create_ppe.html',
        {
            'form': form,
            'ppe': ppe,
            'categories': PPECategory.objects.filter(
                is_active=True
            ),
            'existing_sizes': ppe.sizes.all(),
            'action': 'Edit',
            'title': 'Edit PPE Item'
        }
    )
@login_required
def create_ppe(request):
    if request.method == 'POST':
        form = PPEItemForm(request.POST)
        if form.is_valid():
            ppe = form.save(commit=False)
            ppe.is_active = request.POST.get('is_active') == 'on'
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
        messages.error(
            request,
            "Please correct the errors below."
        )
    else:
        form = PPEItemForm()
    return render(
        request,
        'PPE/configuration/create_ppe.html',
        {
            'form': form,
            'categories': PPECategory.objects.filter(
                is_active=True
            ),
            'ppe_code': PPEItem.generate_ppe_code(),
            'action': 'Create',
            'title': 'Create PPE Item'
        }
    )
@login_required
def ppe_detail(request, pk):
    ppe = get_object_or_404(PPEItem, pk=pk)
    size_quantities = PPESizeQuantity.objects.filter(ppe_item=ppe)
    context = {
        'ppe': ppe,
        'size_quantities' : size_quantities,
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
def stock_list(request):
    search = request.GET.get('search', '')

    stocks = (
        PPEStockTransaction.objects
        .select_related(
            'ppe_item',
            'ppe_item__category'
        )
        .filter(
            transaction_type='OPENING'
        )
        .order_by('-id')
    )
    if search:
        query = (
            Q(ppe_item__name__icontains=search) |
            Q(ppe_item__category__category_name__icontains=search) |
            Q(reference_number__icontains=search)
        )
        try:
            search_date = datetime.strptime(
                search,
                '%d-%m-%Y'
            ).date()
            query |= Q(transaction_date=search_date)
        except ValueError:
            pass
        stocks = stocks.filter(query)
    paginator = Paginator(stocks, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(
        request,
        'ppe/configuration/stock_list.html',
        {
            'page_obj': page_obj,
            'search': search
        }
    )
@login_required
def stock_create(request):
    plant = Plant.objects.filter(
        users=request.user
    ).first()
    form = PPEStockTransactionForm(
        request.POST or None
    )
    selected_item = None
    sizes = []
    category = ""
    ppe_item_id = request.GET.get('ppe_item')
    if ppe_item_id:
        try:
            selected_item = PPEItem.objects.get(
                id=ppe_item_id
            )
            all_sizes = PPESizeQuantity.objects.filter(
                ppe_item=selected_item
            ).order_by('size')
            sizes = []
            seen = set()
            for s in all_sizes:
                if s.size not in seen:
                    sizes.append(s)
                    seen.add(s.size)
            category = selected_item.category.category_name
        except PPEItem.DoesNotExist:
            selected_item = None
    if request.method == "POST":
        plant_id = request.POST.get('plant')
        if not plant_id:
            messages.error(
                request,
                "Please select Plant."
            )
            return redirect('PPE:stock_create')
        plant = Plant.objects.get(
            id=plant_id
        )
        ppe_item_id = request.POST.get(
            'ppe_item'
        )
        if not ppe_item_id:
            messages.error(
                request,
                "Please select PPE Item."
            )
            return redirect('PPE:stock_create')
        ppe_item = PPEItem.objects.get(
            id=ppe_item_id
        )
        transaction_type = request.POST.get(
            'transaction_type'
        )
        unit = request.POST.get(
            'unit'
        )
        transaction_date = request.POST.get(
            'transaction_date'
        )
        reference_number = request.POST.get(
            'reference_number'
        )
        remarks = request.POST.get(
            'remarks'
        )
        size_ids = request.POST.getlist(
            'size_id[]'
        )
        qtys = request.POST.getlist(
            'qty[]'
        )
        size_quantities = {}
        entered_qty = 0
        for size_id, qty in zip(size_ids, qtys):
            if not size_id:
                continue
            try:
                qty = int(qty or 0)
            except ValueError:
                qty = 0
            if qty <= 0:
                continue
            try:
                selected_size = PPESizeQuantity.objects.filter(
                    id=int(size_id),
                    ppe_item=ppe_item
                ).first()
                if not selected_size:
                    messages.error(request, "Size record not found.")
                    return redirect('PPE:stock_create')
                # Check existing PPE + Size + Plant
                size_obj = PPESizeQuantity.objects.filter(
                    ppe_item=ppe_item,
                    size=selected_size.size,
                    plant=plant
                ).first()
                if size_obj:
                    size_obj.available_quantity += qty
                    size_obj.save()
                else:
                    # create new record
                    size_obj = PPESizeQuantity.objects.create(
                        ppe_item=ppe_item,
                        size=selected_size.size,
                        plant=plant,
                        available_quantity=qty
                    )
            except PPESizeQuantity.DoesNotExist:
                messages.error(
                    request,
                    "Size record not found."
                )
                return redirect(
                    'PPE:stock_create'
                )
            size_quantities[str(size_obj.size)] = qty
            entered_qty += qty
        if entered_qty <= 0:
            return render(
                request,
                'ppe/configuration/stock_form.html',
                {
                    'form': form,
                    'selected_item': selected_item,
                    'sizes': sizes,
                    'plants': Plant.objects.filter(is_active=True),
                    'selected_plant': plant,
                    'category': category,
                    'today': timezone.now().date(),
                    'action': 'Create',
                    'error': 'Please enter quantity.'
                }
            )
        PPEStockTransaction.objects.create(
            plant=plant,
            ppe_item=ppe_item,
            size_quantities=size_quantities,
            quantity=entered_qty,
            total=entered_qty,
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
        return redirect(
            'PPE:stock_list'
        )
    plants = Plant.objects.filter(
        is_active=True
    )
    return render(
        request,
        'ppe/configuration/stock_form.html',
        {
            'form': form,
            'selected_item': selected_item,
            'sizes': sizes,
            'plants': plants,
            'selected_plant': None,
            'category': category,
            'today': timezone.now().date(),
            'action': 'Create'
        }
    )
@login_required
def stock_edit(request, pk):
    stock = get_object_or_404(
        PPEStockTransaction,
        pk=pk
    )
    selected_item = stock.ppe_item
    plant_id = request.GET.get('plant')
    ppe_item_id = stock.ppe_item_id
    plant_id = stock.plant_id
    if ppe_item_id and plant_id:
           sizes = PPESizeQuantity.objects.filter(
            ppe_item_id=ppe_item_id,
            plant_id=plant_id
        )
    plants = Plant.objects.filter(
        is_active=True
    )
    category = (
        selected_item.category.category_name
    )
    if request.method == "POST":
        ppe_item_id = request.POST.get(
            'ppe_item'
        )
        plant_id = request.POST.get(
            'plant'
        )
        transaction_type = request.POST.get(
            'transaction_type'
        )
        unit = request.POST.get(
            'unit'
        )
        transaction_date = request.POST.get(
            'transaction_date'
        )
        reference_number = request.POST.get(
            'reference_number'
        )
        remarks = request.POST.get(
            'remarks'
        )
        is_active = bool(
            request.POST.get('is_active')
        )
        size_ids = request.POST.getlist(
            'size_id[]'
        )
        qtys = request.POST.getlist(
            'qty[]'
        )
        if not ppe_item_id:
            messages.error(
                request,
                "Please select PPE Item."
            )
            return redirect(
                'PPE:stock_edit',
                pk=pk
            )
        ppe_item = PPEItem.objects.get(
            id=ppe_item_id
        )
        old_quantities = (
            stock.size_quantities or {}
        )
        size_quantities = {}
        total = 0
        for size_id, qty in zip(
            size_ids,
            qtys
        ):
            try:
                new_qty = int(qty or 0)
            except ValueError:
                new_qty = 0
            size_obj = PPESizeQuantity.objects.filter(
                id=size_id,
                ppe_item=ppe_item
            ).first()
            if not size_obj:
                continue
            old_qty = old_quantities.get(
                str(size_obj.size),
                0
            )
            difference = (
                new_qty - old_qty
            )
            size_obj.available_quantity += difference
            if size_obj.available_quantity < 0:
                size_obj.available_quantity = 0
            size_obj.save()
            size_quantities[
                str(size_obj.size)
            ] = new_qty
            total += new_qty
        if total <= 0:
            messages.error(
                request,
                "Quantity required"
            )
            return render(
                request,
                'ppe/configuration/stock_form.html',
                {
                    'form': PPEStockTransactionForm(
                        instance=stock
                    ),
                    'stock': stock,
                    'plants': plants,
                    'selected_plant': stock.plant,
                    'selected_item': selected_item,
                    'sizes': sizes,
                    'category': category,
                    'action': 'Edit'
                }
            )
        # Update transaction
        stock.plant_id = plant_id
        stock.ppe_item = ppe_item
        stock.transaction_type = transaction_type
        stock.unit = unit
        stock.transaction_date = transaction_date
        stock.reference_number = reference_number
        stock.remarks = remarks
        stock.is_active = is_active
        stock.size_quantities = size_quantities
        stock.quantity = total
        stock.total = total
        stock.updated_by = request.user
        stock.save()
        messages.success(
            request,
            "Stock updated successfully."
        )
        return redirect(
            'PPE:stock_list'
        )
    # Populate saved quantities
    saved_quantities = (
        stock.size_quantities or {}
    )
    for s in sizes:
        s.stock_quantity = (
            saved_quantities.get(
                str(s.size),
                0
            )
        )
    return render(
        request,
        'ppe/configuration/stock_form.html',
        {
            'form': PPEStockTransactionForm(
                instance=stock
            ),
            'stock': stock,
            'plants': plants,
            'selected_plant': stock.plant,
            'selected_item': selected_item,
            'sizes': sizes,
            'category': category,
            'transaction_date': stock.transaction_date,
            'action': 'Edit'
        }
    )
@login_required
def stock_detail(request, pk):
    stock = get_object_or_404(PPEStockTransaction, pk=pk)
    saved_quantities = stock.size_quantities
    return render(request, 'ppe/configuration/stock_detail.html', {
        'stock': stock,
        'saved_quantities': saved_quantities
    })
@login_required
def stock_delete(request, pk):
    stock = get_object_or_404(
        PPEStockTransaction,
        pk=pk
    )
    if request.method == "POST":
        size_quantities = stock.size_quantities or {}
        for size_name, qty in size_quantities.items():
            try:
                size_obj = PPESizeQuantity.objects.get(
                    ppe_item=stock.ppe_item,
                    plant=stock.plant,
                    size=size_name
                )
                qty = int(qty)
                if size_obj.available_quantity > qty:
                    size_obj.available_quantity -= qty
                    size_obj.save()
                else:
                    size_obj.delete()
            except PPESizeQuantity.DoesNotExist:
                pass
        stock.delete()
        messages.success(
            request,
            "Stock deleted successfully."
        )
        return redirect(
            'PPE:stock_list'
        )
    return render(
        request,
        'ppe/configuration/stock_delete.html',
        {
            'stock': stock
        }
    )
@login_required
def IssueManagement_list(request):
    search = request.GET.get('search', '')
    issues = PPEIssueManagement.objects.all()
    if search:
        query = (
            Q(ppe_item__name__icontains=search) |
            Q(issue_group_no__icontains=search)
        )
        try:
            search_date = datetime.strptime(
                search,
                '%d-%m-%Y'
            ).date()
            query |= Q(issue_date=search_date)
        except ValueError:
            pass
        issues = issues.filter(query)
    issues = (
        issues.values(
            'issue_group_no',
            'issue_date',
            'ppe_item__name'
        )
        .annotate(
            total_persons=Count('id'),
            total_qty=Sum('quantity_issue'),
            first_id=Min('id')
        )
        .order_by('-issue_group_no')
    )
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
    form = PPEIssueManagementForm()
    selected_item = None
    available_quantity = 0
    sizes = []
    ppe_item_id = request.GET.get('ppe_item')
    plant_id = request.GET.get('plant')
    plants = Plant.objects.filter(
    is_active=True
    )
    if ppe_item_id:
        plants = plants.filter(
            ppe_transactions__ppe_item_id=ppe_item_id,
            ppe_transactions__transaction_type='OPENING'
        ).distinct()
    issue_date = request.GET.get(
        'issue_date',
        date.today().strftime('%Y-%m-%d')
    )
    employees = User.objects.filter(
        is_active=True
    ).select_related(
        'department'
    )
    # ----------------------------
    # LOAD PPE + SIZE STOCK
    # ----------------------------
    if ppe_item_id:
        try:
            selected_item = PPEItem.objects.get(
                id=ppe_item_id
            )
            if plant_id:
                sizes = PPESizeQuantity.objects.filter(
                    ppe_item_id=ppe_item_id,
                    plant_id=plant_id
                )
                available_quantity = sum(
                    x.available_quantity
                    for x in sizes
                )
        except PPEItem.DoesNotExist:
            selected_item = None
    # ============================
    # SAVE ISSUE
    # ============================
    if request.method == "POST":
        plant_id = request.POST.get("plant")
        ppe_item_id = request.POST.get("ppe_item")
        if not plant_id:
            messages.error(request,"Select Plant")
            return redirect(request.path)
        plant = Plant.objects.get(
            id=int(plant_id)
        )
        ppe_item = PPEItem.objects.get(
            id=int(ppe_item_id)
        )
        size_list = request.POST.getlist("size[]")
        qty_list = request.POST.getlist("quantity_issue[]")
        issue_to_list = request.POST.getlist("issue_to[]")
        employee_list = request.POST.getlist("employee[]")
        contractor_list = request.POST.getlist("contractor_name[]")
        department_list = request.POST.getlist("department[]")
        contractor_department_list = request.POST.getlist("contractor_department[]")
        remarks_list = request.POST.getlist("remarks[]")
        issue_group_no = PPEIssueManagement.generate_issue_no()
        for (
            size_id,
            qty,
            issue_to,
            employee_id,
            contractor_name,
            department_id,
            contractor_department,
            remarks
        ) in zip_longest(
            size_list,
            qty_list,
            issue_to_list,
            employee_list,
            contractor_list,
            department_list,
            contractor_department_list,
            remarks_list,
            fillvalue=''
        ):
            if not size_id or not qty:
                continue
            qty = int(qty)
            selected_size = PPESizeQuantity.objects.filter(
                id=size_id,
                plant_id=plant_id,
                ppe_item_id=ppe_item_id
            ).first()
            if not selected_size:
                messages.error(
                    request,
                    "Stock not available for selected plant"
                )
                return redirect(request.path)
            if qty > selected_size.available_quantity:
                messages.error(
                    request,
                    f"Available stock {selected_size.available_quantity}"
                )
                return redirect(request.path)
            PPEIssueManagement.objects.create(
                plant=plant,   
                issue_group_no=issue_group_no,

                issue_date=request.POST.get(
                    "issue_date"
                ),
                ppe_item=ppe_item,
                available_quantity=selected_size.available_quantity,
                size=selected_size,
                quantity_issue=qty,
                issue_to=issue_to or None,
                employee_id=employee_id or None,
                contractor_name=contractor_name.strip(),
                department_id=department_id or None,
                contractor_department=contractor_department,
                remarks=remarks,
                created_by=request.user
            )
            selected_size.available_quantity -= qty
            selected_size.save()
        messages.success(
            request,
            "PPE Issued Successfully"
        )
        return redirect(
            "PPE:IssueManagement_list"
        )
    context = {
        "form": form,
        "plants": plants,
        "selected_item": selected_item,
        "selected_plant_id": plant_id,
        "available_quantity": available_quantity,
        "sizes": sizes,
        "employees": employees,
        "issue_date": issue_date,
    }
    return render(
        request,
        "ppe/Management/IssueManagement_create.html",
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
    first_issue = get_object_or_404(
        PPEIssueManagement,
        pk=pk
    )
    issues = list(
        PPEIssueManagement.objects.filter(
            issue_group_no=first_issue.issue_group_no
        ).order_by('id')
    )
    # Prevent edit if return already exists
    issue_ids = PPEIssueManagement.objects.filter(
        issue_group_no=first_issue.issue_group_no
    ).values_list(
        'id',
        flat=True
    )
    return_exists = PPEReturnManagement.objects.filter(
        issue_id__in=issue_ids
    ).exists()
    if return_exists:
        messages.error(
            request,
            "This Issue cannot be edited because Return entry already exists against it."
        )
        return redirect(
            'PPE:IssueManagement_list'
        )
    size_stock = {}
    for issue in issues:
        size_id = issue.size.id
        if size_id not in size_stock:
            total_issued = (
                PPEIssueManagement.objects.filter(
                    issue_group_no=issue.issue_group_no,
                    size=issue.size
                ).aggregate(
                    total=Sum('quantity_issue')
                )['total'] or 0
            )
            size_stock[size_id] = (
                issue.size.available_quantity +
                total_issued
            )
        issue.display_stock = size_stock[size_id]
        size_stock[size_id] -= issue.quantity_issue
    original_stock = {}
    for issue in issues:
        size_id = issue.size.id
        if size_id not in original_stock:
            total_issued = (
                PPEIssueManagement.objects.filter(
                    issue_group_no=issue.issue_group_no,
                    size=issue.size
                ).aggregate(
                    total=Sum('quantity_issue')
                )['total'] or 0
            )
            original_stock[size_id] = (
                issue.size.available_quantity +
                total_issued
            )
    employees = User.objects.filter(
        is_active=True
    ).select_related(
        'department'
    )
    selected_item = first_issue.ppe_item
    available_quantity = (
        PPESizeQuantity.objects.filter(
            ppe_item=first_issue.ppe_item
        ).aggregate(
            total=Sum('available_quantity')
        )['total'] or 0
    )
    sizes = PPESizeQuantity.objects.filter(
    ppe_item=selected_item,
    plant=first_issue.plant
    )
    for size in sizes:
        size.original_qty = original_stock.get(
            size.id,
            size.available_quantity
        )
    if request.method == 'POST':
        issue_date = request.POST.get(
            'issue_date'
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
        old_issues = PPEIssueManagement.objects.filter(
            issue_group_no=first_issue.issue_group_no
        )
        for obj in old_issues:
            obj.size.available_quantity += (
                obj.quantity_issue
            )
            obj.size.save()
        old_issues.delete()
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
            size_obj = PPESizeQuantity.objects.get(
                id=size_id
            )
            if qty > size_obj.available_quantity:
                messages.error(
                    request,
                    f"{size_obj.size} has only "
                    f"{size_obj.available_quantity} available."
                )
                return redirect(
                    'PPE:edit_issue',
                    pk=pk
                )
            employee = None
            if employee_id:
                employee = User.objects.get(
                    id=employee_id
                )
            PPEIssueManagement.objects.create(
                plant=first_issue.plant,
                issue_group_no=first_issue.issue_group_no,
                issue_date=issue_date,
                ppe_item=first_issue.ppe_item,
                available_quantity=size_obj.available_quantity,
                issue_to=issue_to,
                employee=employee,
                contractor_name=contractor_name,
                contractor_department=contractor_department,
                department_id=department_id if department_id else None,
                size=size_obj,
                quantity_issue=qty,
                remarks=remarks,
                created_by=request.user
            )
            size_obj.available_quantity -= qty
            size_obj.save()
        # -------------------------
        # Update Stock Transaction
        # -------------------------
        total_available = (
            PPESizeQuantity.objects.filter(
                ppe_item=first_issue.ppe_item,
                plant=first_issue.plant
            ).aggregate(
                total=Sum('available_quantity')
            )['total'] or 0
        )

        latest_stock = (
            PPEStockTransaction.objects.filter(
                plant=first_issue.plant,
                ppe_item=first_issue.ppe_item
            )
            .order_by('-id')
            .first()
        )

        if latest_stock:
            latest_stock.quantity = total_available
            latest_stock.total = total_available
            latest_stock.save()

        messages.success(
            request,
            "Issue Updated Successfully."
        )

        return redirect(
            'PPE:IssueManagement_list'
        )
    ppe_items = PPEItem.objects.filter(
    is_active=True
    )
    form = PPEIssueManagementForm()
    context = {
        'form':form,
        'ppe_items': ppe_items,
        'issues': issues,
        'issue': first_issue,
        'selected_item': selected_item,
        'plants': Plant.objects.filter(
                is_active=True,
            ),
            'selected_plant_id': str(
                first_issue.plant_id
            ),
        'available_quantity': available_quantity,
        'sizes': sizes,
        'employees': employees,
        'edit_mode': True,
        'original_stock': original_stock,
    }
    return render(
        request,
        'ppe/Management/IssueManagement_create.html',
        context
    )
@login_required
def issue_detail(request, pk):
    first_issue = get_object_or_404(PPEIssueManagement.objects.select_related(
            'employee',
            'department',
            'size',
            'plant'
        ),pk=pk)
    issues = PPEIssueManagement.objects.filter(issue_group_no=first_issue.issue_group_no).select_related(
        'employee','department','size','plant').order_by('id')
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
    issue = get_object_or_404(
        PPEIssueManagement,
        pk=pk
    )
    if request.method == "POST":
        issues = PPEIssueManagement.objects.filter(
            issue_group_no=issue.issue_group_no
        )
        for item in issues:

            size_obj = item.size

            if size_obj:
                size_obj.available_quantity += (
                    item.quantity_issue
                )
                size_obj.save()
        issues.delete()
        messages.success(
            request,
            "Issue deleted successfully."
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
@login_required
def return_list(request):
    search = request.GET.get('search', '')
    returns = (
        PPEReturnManagement.objects
        .select_related(
            'plant',
            'ppe_item'
        )
        .values(
            'return_date',
            'plant_id',
            'plant__name',
            'ppe_item__name'
        )
        .annotate(
            assigned_qty=Sum('assigned_qty'),
            total_return_qty=Sum('return_qty'),
            first_id=Min('id')
        )
        .order_by(
            '-return_date',
            'plant__name'
        )
    )
    if search:
        query = (
            Q(ppe_item__name__icontains=search) |
            Q(plant__name__icontains=search)
        )
        try:
            search_date = datetime.strptime(
                search,
                '%d-%m-%Y'
            ).date()
            query |= Q(
                return_date=search_date
            )
        except ValueError:
            pass
        returns = returns.filter(query)
    return render(
        request,
        'PPE/management/return_list.html',
        {
            'page_obj': returns,
            'search': search,
        }
    )
@login_required
def return_create(request):
    form = PPEReturnManagementForm()
    ppe_item_id = request.GET.get('ppe_item') or request.POST.get('ppe_item')
    plant_id = request.GET.get('plant') or request.POST.get('plant')
    plants = Plant.objects.filter(
        is_active=True
    )
    if ppe_item_id:
        plants = plants.filter(
            ppe_transactions__ppe_item_id=ppe_item_id,
            ppe_transactions__transaction_type='OPENING'
        ).distinct()
    # -----------------------------
    # PPE TOTALS
    # -----------------------------
    ppe_totals = {}
    for item in PPEItem.objects.filter(is_active=True):
        qty_qs = PPESizeQuantity.objects.filter(
            ppe_item=item
        )
        if plant_id:
            qty_qs = qty_qs.filter(
                plant_id=plant_id
            )
        ppe_totals[str(item.id)] = sum(
            x.available_quantity
            for x in qty_qs
        )
    available_quantity = 0
    if ppe_item_id and plant_id:
        sizes = PPESizeQuantity.objects.filter(
            ppe_item_id=ppe_item_id,
            plant_id=plant_id
        )
        available_quantity = sum(
            x.available_quantity
            for x in sizes
        )
    issues = PPEIssueManagement.objects.select_related(
        'ppe_item',
        'employee',
        'department',
        'size',
        'plant'
    )
    if plant_id:
        issues = issues.filter(
            plant_id=plant_id
        )
    if ppe_item_id:
        issues = issues.filter(
            ppe_item_id=ppe_item_id
        )
    filtered_issues = []
    for issue in issues:
        returned_qty = (
            PPEReturnManagement.objects
            .filter(issue=issue)
            .aggregate(
                total=Sum('return_qty')
            )['total'] or 0
        )
        balance_qty = (
            issue.quantity_issue -
            returned_qty
        )
        if balance_qty > 0:
            issue.balance_qty = balance_qty
            issue.employee_name = (
                issue.employee.get_full_name()
                if issue.employee
                else issue.contractor_name
            )
            filtered_issues.append(issue)
    # =============================
    # SAVE RETURN
    # =============================
    if request.method == "POST":
        return_date = request.POST.get('return_date')
        issue_list = request.POST.getlist('issue[]')
        return_qty_list = request.POST.getlist('return_qty[]')
        return_group_no = (
            PPEReturnManagement.generate_return_group_no()
        )
        for issue_id, return_qty in zip(
            issue_list,
            return_qty_list,
        ):
            if not issue_id or not return_qty:
                continue
            issue = (
                PPEIssueManagement.objects
                .select_related(
                    'ppe_item',
                    'employee',
                    'department',
                    'size',
                    'plant'
                )
                .get(id=issue_id)
            )
            return_qty = int(return_qty)
            already_returned = (
                PPEReturnManagement.objects
                .filter(issue=issue)
                .aggregate(
                    total=Sum('return_qty')
                )['total'] or 0
            )
            balance_qty = (
                issue.quantity_issue -
                already_returned
            )
            if return_qty > balance_qty:
                messages.error(
                    request,
                    f"Only {balance_qty} available for return."
                )
                return redirect(
                    'PPE:return_create'
                )
            # Update stock
            current_stock = issue.size
            current_stock.available_quantity += return_qty
            current_stock.save()
            try:
                obj = PPEReturnManagement.objects.create(
                    return_group_no=return_group_no,
                    issue=issue,
                    return_date=return_date,
                    return_qty=return_qty,
                    created_by=request.user,
                    updated_by=request.user
                )
            except Exception as e:
                print("ERROR TYPE:", type(e))
                print("ERROR =", str(e))
                raise
        messages.success(
                request,
                "PPE Returned Successfully."
        )
        return redirect(
                'PPE:return_list'
        )
    return render(
        request,
        'PPE/management/return_create.html',
        {
            'form': form,
            'return_date': date.today().strftime(
                '%Y-%m-%d'
            ),
            'ppe_items': PPEItem.objects.filter(
                is_active=True
            ),
            'plants': plants,
            'issues': filtered_issues,
            'ppe_totals': ppe_totals,
            'available_quantity': available_quantity,
            'selected_plant_id': str(plant_id or ''),
            'selected_ppe_id': str(ppe_item_id or ''),
        }
    )
@login_required
def get_issue_details(request):
    issue_id = request.GET.get('issue_id')
    try:
        issue = PPEIssueManagement.objects.select_related(
            'ppe_item',
            'employee',
            'department',
            'size'
        ).get(id=issue_id)

        data = {
            'issue_no': issue.issue_no,
            'ppe_item': str(issue.ppe_item),
            'available_qty': issue.available_quantity,
            'return_to': issue.issue_to,
            'employee': issue.employee.get_full_name() if issue.employee else '',
            'contractor_name': issue.contractor_name or '',
            'department': str(issue.department) if issue.department else '',
            'contractor_department': issue.contractor_department or '',
            'size': str(issue.size),
            'assigned_qty': issue.quantity_issue,
        }
        return JsonResponse(data)
    except PPEIssueManagement.DoesNotExist:
        return JsonResponse(
            {'error': 'Issue not found'},
            status=404
        )
@login_required
def return_delete(request, pk):
    return_obj = get_object_or_404(
        PPEReturnManagement,
        pk=pk
    )
    if request.method == "POST":
        # Get only records of this return transaction
        return_records = (
            PPEReturnManagement.objects.filter(
                return_group_no=return_obj.return_group_no
            )
        )
        # Validate stock before rollback
        for obj in return_records:
            size_obj = obj.size
            new_qty = (
                size_obj.available_quantity -
                obj.return_qty
            )
            if new_qty < 0:
                messages.error(
                    request,
                    f"Cannot delete return. "
                    f"Available quantity for Size "
                    f"{size_obj.size} would become negative."
                )
                return redirect(
                    'PPE:return_list'
                )
        # Reverse stock
        for obj in return_records:
            size_obj = obj.size
            size_obj.available_quantity -= (
                obj.return_qty
            )
            size_obj.save()
        # Delete only this return group
        return_records.delete()
        messages.success(
            request,
            "Return deleted successfully"
        )
        return redirect(
            'PPE:return_list'
        )
    return render(
        request,
        'PPE/management/return_delete.html',
        {
            'return_obj': return_obj
        }
    )
@login_required
def return_edit(request, pk):
    return_obj = get_object_or_404(
        PPEReturnManagement,
        pk=pk
    )
    return_rows = PPEReturnManagement.objects.filter(
        return_group_no=return_obj.return_group_no
    )
    # =====================================================
    # UPDATE RETURN
    # =====================================================
    if request.method == "POST":
        return_date = request.POST.get("return_date")
        issue_list = request.POST.getlist("issue[]")
        return_qty_list = request.POST.getlist("return_qty[]")
        # ----------------------------------
        # VALIDATION
        # ----------------------------------
        for issue_id, return_qty in zip_longest(
            issue_list,
            return_qty_list,
        ):
            if not issue_id or not return_qty:
                continue
            try:
                issue = PPEIssueManagement.objects.get(
                    id=issue_id
                )
                return_qty = int(return_qty)

            except (
                PPEIssueManagement.DoesNotExist,
                ValueError
            ):
                continue
            returned_qty = (
                PPEReturnManagement.objects.filter(
                    issue=issue
                )
                .exclude(
                    return_group_no=return_obj.return_group_no
                )
                .aggregate(
                    total=Sum('return_qty')
                )['total'] or 0
            )
            balance_qty = (
                issue.quantity_issue -
                returned_qty
            )
            if return_qty > balance_qty:
                messages.error(
                    request,
                    f"Only {balance_qty} quantity can be returned for Size {issue.size.size}."
                )
                return redirect(
                    'PPE:return_edit',
                    pk=pk
                )
        # ----------------------------------
        # FETCH PREVIOUS STOCK
        # ----------------------------------
        for row in return_rows:
            size_obj = PPESizeQuantity.objects.get(
                pk=row.size.pk,
                plant=row.plant
            )
            size_obj.available_quantity -= row.return_qty
            size_obj.save()
        return_rows.delete()
        for issue_id, return_qty in zip_longest(
            issue_list,
            return_qty_list,
            ):
            if not issue_id or not return_qty:
                continue
            try:
                issue = (
                    PPEIssueManagement.objects
                    .select_related(
                        'ppe_item',
                        'employee',
                        'department',
                        'size',
                        'plant'
                    )
                    .get(id=issue_id)
                )
                return_qty = int(return_qty)
            except (
                PPEIssueManagement.DoesNotExist,
                ValueError
            ):
                continue
            plant_available_qty = (
                PPESizeQuantity.objects.filter(
                    ppe_item=issue.ppe_item,
                    plant=issue.plant
                ).aggregate(
                    total=Sum('available_quantity')
                )['total'] or 0
            )
            updated_available_qty = (
                plant_available_qty +
                return_qty
            )
            return_no = (
                PPEReturnManagement.generate_return_no()
            )
            PPEReturnManagement.objects.create(
                return_group_no=return_obj.return_group_no,
                return_no=return_no,
                plant=issue.plant,
                issue=issue,
                return_date=return_date,
                ppe_item=issue.ppe_item,
                available_qty=updated_available_qty,
                return_to=issue.issue_to,
                employee=issue.employee,
                contractor_name=issue.contractor_name,
                contractor_department=issue.contractor_department,
                department=issue.department,
                size=issue.size,
                assigned_qty=issue.quantity_issue,
                return_qty=return_qty,
                created_by=return_obj.created_by,
                updated_by=request.user
            )
            size_obj = PPESizeQuantity.objects.get(
                pk=issue.size.pk,
                plant=issue.plant
            )
            size_obj.available_quantity += return_qty
            size_obj.save()
        messages.success(
            request,
            "Return updated successfully."
        )
        return redirect(
            'PPE:return_list'
        )
    form = PPEReturnManagementForm()
    plant_id = str(return_obj.plant.id)
    plants = Plant.objects.filter(
        ppe_transactions__transaction_type='OPENING',
        is_active=True
    ).distinct()
    ppe_totals = {}
    for item in PPEItem.objects.filter(
        is_active=True
    ):
        qty_qs = PPESizeQuantity.objects.filter(
            ppe_item=item
        )
        ppe_totals[str(item.id)] = sum(
            obj.available_quantity
            for obj in qty_qs
        )
    issues = PPEIssueManagement.objects.select_related(
        'ppe_item',
        'employee',
        'department',
        'size',
        'plant'
    ).filter(
        plant_id=plant_id,
        quantity_issue__gt=0
    )
    filtered_issues = []
    for issue in issues:
        returned_qty = (
            PPEReturnManagement.objects.filter(
                issue=issue
            ).exclude(
                return_group_no=return_obj.return_group_no
            ).aggregate(
                total=Sum('return_qty')
            )['total'] or 0
        )
        balance_qty = (
            issue.quantity_issue -
            returned_qty
        )
        if balance_qty > 0:
            issue.balance_qty = balance_qty
            filtered_issues.append(issue)
    context = {
        'edit_mode': True,
        'form': form,
        'return_obj': return_obj,
        'return_rows': return_rows,
        'return_date': return_obj.return_date.strftime(
            '%Y-%m-%d'
        ),
        'ppe_items': PPEItem.objects.filter(
            is_active=True
        ),
        'plants': plants,
        'issues': filtered_issues,
        'ppe_totals': ppe_totals,
        'available_quantity': return_obj.available_qty,
        'selected_plant_id': plant_id,
    }
    return render(
        request,
        'PPE/management/return_create.html',
        context
    )
@login_required
def return_detail(request, pk):
    first_return = get_object_or_404(
        PPEReturnManagement,
        pk=pk
    )
    returns = (
        PPEReturnManagement.objects
        .filter(
            return_group_no=first_return.return_group_no
        )
        .select_related(
            'employee',
            'department',
            'size',
            'ppe_item',
            'plant'
        )
        .order_by('id')
    )
    totals = returns.aggregate(
        total_assigned_qty=Sum(
            'assigned_qty'
        ),
        total_return_qty=Sum(
            'return_qty'
        )
    )
    context = {
        'return_obj': first_return,
        'returns': returns,
        'plant_name': (
            first_return.plant.name
            if first_return.plant
            else ''
        ),
        'total_assigned_qty':
            totals['total_assigned_qty'] or 0,
        'total_return_qty':
            totals['total_return_qty'] or 0,
    }
    return render(
        request,
        'PPE/management/return_detail.html',
        context
    )