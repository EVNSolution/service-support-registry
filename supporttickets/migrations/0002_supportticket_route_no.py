from django.db import migrations, models


def populate_support_ticket_route_no(apps, schema_editor):
    SupportTicket = apps.get_model("supporttickets", "SupportTicket")
    for index, ticket in enumerate(SupportTicket.objects.order_by("created_at", "ticket_id"), start=1):
        ticket.route_no = index
        ticket.save(update_fields=["route_no"])


class Migration(migrations.Migration):
    dependencies = [
        ("supporttickets", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="supportticket",
            name="route_no",
            field=models.PositiveIntegerField(editable=False, null=True, unique=True),
        ),
        migrations.RunPython(populate_support_ticket_route_no, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="supportticket",
            name="route_no",
            field=models.PositiveIntegerField(editable=False, unique=True),
        ),
    ]
