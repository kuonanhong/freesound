#
# Freesound is (c) MUSIC TECHNOLOGY GROUP, UNIVERSITAT POMPEU FABRA
#
# Freesound is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# Freesound is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# Authors:
#     See AUTHORS file.
#

from django.shortcuts import render
from django.conf import settings
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import redirect
from sounds.models import Sound
import gearman
import tickets.views
import sounds.views


@staff_member_required
def monitor_home(request):
    sounds_in_moderators_queue_count =\
        tickets.views._get_sounds_in_moderators_queue_count(request.user)

    new_upload_count = tickets.views.new_sound_tickets_count()
    tardy_moderator_sounds_count =\
        len(tickets.views._get_tardy_moderator_tickets())

    tardy_user_sounds_count = len(tickets.views._get_tardy_user_tickets())

    sounds_queued_count = sounds.views.Sound.objects.filter(
            processing_ongoing_state='QU').count()
    sounds_pending_count = sounds.views.Sound.objects.filter(
            processing_state='PE').count()
    sounds_processing_count = sounds.views.Sound.objects.filter(
            processing_ongoing_state='PR').count()
    sounds_failed_count = sounds.views.Sound.objects.filter(
            processing_state='FA').count()

    # Get gearman status
    try:
        gm_admin_client = gearman.GearmanAdminClient(settings.GEARMAN_JOB_SERVERS)
        gearman_status = gm_admin_client.get_status()
    except gearman.errors.ServerUnavailable:
        gearman_status = list()

    tvars = {"new_upload_count": new_upload_count,
             "tardy_moderator_sounds_count": tardy_moderator_sounds_count,
             "tardy_user_sounds_count": tardy_user_sounds_count,
             "sounds_queued_count": sounds_queued_count,
             "sounds_pending_count": sounds_pending_count,
             "sounds_processing_count": sounds_processing_count,
             "sounds_failed_count": sounds_failed_count,
             "gearman_status": gearman_status,
             "sounds_in_moderators_queue_count": sounds_in_moderators_queue_count}

    return render(request, 'monitor/monitor.html', tvars)


@login_required
@user_passes_test(lambda u: u.is_staff, login_url='/')
def process_sounds(request, processing_status):

    sounds_to_process = None
    if processing_status == "FA":
        sounds_to_process = Sound.objects.filter(processing_state='FA')
    elif processing_status == "PE":
        sounds_to_process = Sound.objects.filter(processing_state='PE')

    # Remove sounds from the list that are already in the queue or are being processed right now
    if sounds_to_process:
        sounds_to_process = sounds_to_process.exclude(processing_ongoing_state='PR')\
            .exclude(processing_ongoing_state='QU')
        for sound in sounds_to_process:
            sound.process()

    return redirect("monitor-home")
