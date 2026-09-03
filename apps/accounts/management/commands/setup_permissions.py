from django.core.management.base import BaseCommand
from apps.accounts.models import Permissions, Role

class Command(BaseCommand):
    help = 'Setup default permissions and roles for EHS-360'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.SUCCESS('Starting permission setup...'))
        
        # Step 1: Create Permissions
        self.create_permissions()
        
        # Step 2: Create Roles with Permissions
        self.create_roles()
        
        self.stdout.write(self.style.SUCCESS('\n✓ Permission setup completed successfully!'))
    
    def create_permissions(self):
        """Create all system permissions"""
        self.stdout.write('\n📋 Creating permissions...')
        
        permissions_data = [
            # Dashboard Permissions
            ('ACCESS_DASHBOARD', 'Access Dashboard', 'Can access system dashboards'),
            ('INJURY_DASHBOARD', 'Access Injury Dashboard', 'Can view injury dashboard'),
            ('HAZARD_DASHBOARD', 'Access Hazard Dashboard', 'Can view hazard dashboard'),
            ('INSPECTION_DASHBOARD', 'Access Inspection Dashboard', 'Can view inspection dashboard'),
            # Emergency Permissions
            ('CREATE_EMERGENCY_REPORT', 'Create Emergency Report', 'Can create/report new emergency reports'),
            ('VIEW_EMERGENCY_REPORT', 'View Emergency Report', 'Can view emergency report details'),

            # Injury Permissions
            ('CREATE_INJURY', 'Create Injury', 'Can create/report new injuries'),
            ('EDIT_INJURY', 'Edit Injury', 'Can edit injury reports'),
            # ('DELETE_INJURY', 'Delete Injury', 'Can delete injuries'),
            ('VIEW_INJURY', 'View Injury', 'Can view injury details'),
            ('APPROVE_INJURY', 'Approve Injury', 'Can approve/reject injury reports'),
            ('CLOSE_INJURY', 'Close Injury', 'Can close completed injuries'),
            
            # Hazard Permissions
            ('CREATE_HAZARD', 'Create Hazard', 'Can create/report new hazards'),
            ('EDIT_HAZARD', 'Edit Hazard', 'Can edit hazard reports'),
            # ('DELETE_HAZARD', 'Delete Hazard', 'Can delete hazards'),
            ('VIEW_HAZARD', 'View Hazard', 'Can view hazard details'),
            # ('APPROVE_HAZARD', 'Approve Hazard', 'Can approve/reject hazard reports'),
            # ('CLOSE_HAZARD', 'Close Hazard', 'Can close resolved hazards'),
            
            # Inspection Permissions
            ('CREATE_INSPECTION', 'Create Inspection', 'Can create/schedule inspections'),
            ('EDIT_INSPECTION', 'Edit Inspection', 'Can edit inspection reports'),
            ('DELETE_INSPECTION', 'Delete Inspection', 'Can delete inspections'),
            ('VIEW_INSPECTION', 'View Inspection', 'Can view inspection details'),
            ('EXPORT_INSPECTION_PDF', 'Export Inspection PDF', 'Can export inspection reports'),
            ('APPROVE_INSPECTION', 'Approve Inspection', 'Can approve inspection reports'),
            ('MANAGE_INSPECTION_CONFIGURATION', 'Manage Inspection Configuration', ''),
            
            # Module Access Permissions
            ('ACCESS_INJURY_MODULE', 'Access Injury Module', 'Can access injury management module'),
            ('ACCESS_HAZARD_MODULE', 'Access Hazard Module', 'Can access hazard management module'),
            ('ACCESS_INSPECTION_MODULE', 'Access Inspection Module', 'Can access inspection module'),
            ('ACCESS_EMERGENCY_MODULE', 'Access Emergency Module', 'Can access emergency module'),
            ('ACCESS_CAPA_MODULE', 'Access CAPA Module', 'Can access CAPA module'),
            # ('ACCESS_AUDIT_MODULE', 'Access Audit Module', 'Can access audit module'),
            # ('ACCESS_TRAINING_MODULE', 'Access Training Module', 'Can access training module'),
            # ('ACCESS_PERMIT_MODULE', 'Access Permit Module', 'Can access work permit module'),
            # ('ACCESS_OBSERVATION_MODULE', 'Access Observation Module', 'Can access safety observation module'),
            # ('ACCESS_REPORTS_MODULE', 'Access Reports Module', 'Can access reports and analytics'),
            
            # Other Permissions
            ('APPROVE_PERMIT', 'Approve Permit', 'Can approve work permit requests'),
            ('CAPA_VIEW', 'View CAPA', 'Can view CAPA records'),
            ('CAPA_CREATE', 'Create CAPA', 'Can create CAPA records'),
            ('CAPA_EDIT', 'Edit CAPA', 'Can edit CAPA records'),
            ('CAPA_ASSIGN', 'Assign CAPA', 'Can assign CAPA owners and actions'),
            ('CAPA_INVESTIGATE', 'Investigate CAPA', 'Can perform CAPA investigation'),
            ('CAPA_RCA', 'CAPA Root Cause Analysis', 'Can perform root cause analysis'),
            ('CAPA_APPROVE_INVESTIGATION', 'Approve CAPA Investigation', 'Can approve or reject CAPA investigation'),
            ('CAPA_MANAGE_ACTIONS', 'Manage CAPA Actions', 'Can manage CAPA actions'),
            ('CAPA_COMPLETE_ACTION', 'Complete CAPA Action', 'Can complete CAPA actions'),
            ('CAPA_VERIFY_ACTION', 'Verify CAPA Action', 'Can verify CAPA actions'),
            ('CAPA_EFFECTIVENESS', 'CAPA Effectiveness Review', 'Can perform effectiveness reviews'),
            ('CAPA_CLOSE', 'Close CAPA', 'Can close CAPA records'),
            ('CAPA_REOPEN', 'Reopen CAPA', 'Can reopen CAPA records'),
            ('CAPA_EXPORT', 'Export CAPA', 'Can export CAPA reports'),
        ]
        
        for code, name, description in permissions_data:
            perm, created = Permissions.objects.get_or_create(
                code=code,
                defaults={'name': name, 'description': description}
            )
            if created:
                self.stdout.write(f'  ✓ Created: {code}')
            else:
                self.stdout.write(f'  - Exists: {code}')
    
    def create_roles(self):
        """Create roles and assign permissions"""
        self.stdout.write('\n👥 Creating roles...')
        
        # ADMIN Role
        self.create_admin_role()
        
        # SAFETY MANAGER Role
        self.create_safety_manager_role()
        
        # HOD Role
        self.create_hod_role()
        
        # PLANT HEAD Role
        self.create_plant_head_role()
        
        # LOCATION HEAD Role
        self.create_location_head_role()
        
        # EMPLOYEE Role
        self.create_employee_role()
    
    def create_admin_role(self):
        """Create ADMIN role with all permissions"""
        role, created = Role.objects.get_or_create(
            name='ADMIN',
            defaults={'description': 'System administrator with full access to all modules'}
        )
        
        if created or True:  # Always update permissions
            # Admin gets ALL permissions
            all_perms = Permissions.objects.all()
            role.permissions.set(all_perms)
            self.stdout.write(f'  ✓ {"Created" if created else "Updated"}: ADMIN role ({all_perms.count()} permissions)')
    
    def create_safety_manager_role(self):
        """Create SAFETY MANAGER role"""
        role, created = Role.objects.get_or_create(
            name='SAFETY MANAGER',
            defaults={'description': 'Safety manager with approval and closure rights'}
        )
        
        if created or True:
            perm_codes = [
                # Full injury access
                'CREATE_INJURY', 'EDIT_INJURY', 'VIEW_INJURY', 
                'APPROVE_INJURY', 'CLOSE_INJURY',
                
                # Full hazard access
                'CREATE_HAZARD', 'EDIT_HAZARD', 'VIEW_HAZARD',
                # 'APPROVE_HAZARD', 'CLOSE_HAZARD',
                
                # Full inspection access
                'CREATE_INSPECTION', 'EDIT_INSPECTION', 'VIEW_INSPECTION', 'EXPORT_INSPECTION_PDF',
                # 'APPROVE_INSPECTION',
                'CAPA_VIEW', 'CAPA_CREATE', 'CAPA_EDIT', 'CAPA_INVESTIGATE', 'CAPA_APPROVE_INVESTIGATION',
                'CAPA_MANAGE_ACTIONS', 'CAPA_COMPLETE_ACTION', 'CAPA_VERIFY_ACTION', 'CAPA_EFFECTIVENESS',
                'CAPA_CLOSE', 'CAPA_REOPEN', 'CAPA_EXPORT',
                
                # Module access
                'ACCESS_INJURY_MODULE', 'ACCESS_HAZARD_MODULE',
                'ACCESS_INSPECTION_MODULE', 'ACCESS_CAPA_MODULE',
                # 'ACCESS_AUDIT_MODULE','ACCESS_REPORTS_MODULE',
            ]
            perms = Permissions.objects.filter(code__in=perm_codes)
            role.permissions.set(perms)
            self.stdout.write(f'  ✓ {"Created" if created else "Updated"}: SAFETY MANAGER role ({perms.count()} permissions)')
    
    def create_hod_role(self):
        """Create HOD (Head of Department) role"""
        role, created = Role.objects.get_or_create(
            name='HOD',
            defaults={'description': 'Head of Department with approval rights'}
        )
        
        if created or True:
            perm_codes = [
                # Can create and view
                'CREATE_INJURY', 'VIEW_INJURY', 'EDIT_INJURY',
                'CREATE_HAZARD', 'VIEW_HAZARD', 'EDIT_HAZARD',
                # 'APPROVE_HAZARD',  # HODs can approve hazards
                
                # Inspection access
                'VIEW_INSPECTION', 'EXPORT_INSPECTION_PDF', #'APPROVE_INSPECTION',
                'CAPA_VIEW', 'CAPA_CREATE', 'CAPA_INVESTIGATE',
                
                # Module access
                'ACCESS_INJURY_MODULE', 'ACCESS_HAZARD_MODULE',
                'ACCESS_INSPECTION_MODULE', 'ACCESS_CAPA_MODULE', #'ACCESS_REPORTS_MODULE',
            ]
            perms = Permissions.objects.filter(code__in=perm_codes)
            role.permissions.set(perms)
            self.stdout.write(f'  ✓ {"Created" if created else "Updated"}: HOD role ({perms.count()} permissions)')
    
    def create_plant_head_role(self):
        """Create PLANT HEAD role"""
        role, created = Role.objects.get_or_create(
            name='PLANT HEAD',
            defaults={'description': 'Plant head with approval rights for plant operations'}
        )
        
        if created or True:
            perm_codes = [
                # Injury access
                'CREATE_INJURY', 'VIEW_INJURY', 'EDIT_INJURY',
                'APPROVE_INJURY',
                
                # Hazard access
                'CREATE_HAZARD', 'VIEW_HAZARD', 'EDIT_HAZARD',
                # 'APPROVE_HAZARD',
                
                # Inspection and permits
                'VIEW_INSPECTION', 'EXPORT_INSPECTION_PDF', 'APPROVE_PERMIT',
                'CAPA_VIEW', 'CAPA_CREATE', 'CAPA_INVESTIGATE', 'CAPA_APPROVE_INVESTIGATION',
                
                # Module access
                'ACCESS_INJURY_MODULE', 'ACCESS_HAZARD_MODULE',
                'ACCESS_INSPECTION_MODULE', 'ACCESS_CAPA_MODULE',
                #'ACCESS_PERMIT_MODULE','ACCESS_REPORTS_MODULE',
            ]
            perms = Permissions.objects.filter(code__in=perm_codes)
            role.permissions.set(perms)
            self.stdout.write(f'  ✓ {"Created" if created else "Updated"}: PLANT HEAD role ({perms.count()} permissions)')
    
    def create_location_head_role(self):
        """Create LOCATION HEAD role"""
        role, created = Role.objects.get_or_create(
            name='LOCATION HEAD',
            defaults={'description': 'Location head with basic approval rights'}
        )
        
        if created or True:
            perm_codes = [
                # Basic reporting
                'CREATE_INJURY', 'VIEW_INJURY',
                'CREATE_HAZARD', 'VIEW_HAZARD', 'CAPA_VIEW', #'APPROVE_HAZARD',
                
                # Module access
                'ACCESS_INJURY_MODULE', 'ACCESS_HAZARD_MODULE', 'ACCESS_CAPA_MODULE',
                #'ACCESS_OBSERVATION_MODULE',
            ]
            perms = Permissions.objects.filter(code__in=perm_codes)
            role.permissions.set(perms)
            self.stdout.write(f'  ✓ {"Created" if created else "Updated"}: LOCATION HEAD role ({perms.count()} permissions)')
    
    def create_employee_role(self):
        """Create EMPLOYEE role"""
        role, created = Role.objects.get_or_create(
            name='EMPLOYEE',
            defaults={'description': 'Regular employee with basic reporting access'}
        )
        
        if created or True:
            perm_codes = [
                # Can only create and view own reports
                'CREATE_INJURY', 'VIEW_INJURY',
                'CREATE_HAZARD', 'VIEW_HAZARD', 'CAPA_VIEW',
                
                # Module access
                'ACCESS_INJURY_MODULE', 'ACCESS_HAZARD_MODULE', 'ACCESS_CAPA_MODULE',
                # 'ACCESS_OBSERVATION_MODULE', 'ACCESS_TRAINING_MODULE',
            ]
            perms = Permissions.objects.filter(code__in=perm_codes)
            role.permissions.set(perms)
            self.stdout.write(f'  ✓ {"Created" if created else "Updated"}: EMPLOYEE role ({perms.count()} permissions)')
