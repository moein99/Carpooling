from django.contrib import admin
from account.models import Member, Report
from django.db.models import Count, Q


@admin.register(Member)
class MemberAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'report_count',
    )

    def get_queryset(self, request):
        return Member.objects.annotate(report_count=Count('reported', filter=Q(reported__resolved=False)))

    def report_count(self, obj):
        return obj.report_count

    report_count.short_description = 'Unresolved Report count'
    report_count.admin_order_field = 'report_count'


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    search_fields = ['id', 'reported__username']

