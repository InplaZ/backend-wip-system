from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('wip', '0004_incore_fields')]

    operations = [
        migrations.AddField('movimientowip', 'registrado_por', models.CharField(blank=True, default='', max_length=150)),
    ]
