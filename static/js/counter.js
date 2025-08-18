

// Nie ruszać bo umrze!!!


document.addEventListener('DOMContentLoaded', function () {
    const endElement = document.getElementById('time_to_end');
    const startElement = document.getElementById('time_to_start');

    if (endElement) {
        const timeToEnd = endElement.getAttribute('data-endtime');
        if (timeToEnd) {
            startCountdown(parseInt(timeToEnd), 'end');
        }
    }

    if (startElement) {
        const timeToStart = startElement.getAttribute('data-starttime');
        if (timeToStart) {
            startCountdown(parseInt(timeToStart), 'start');
        }
    }
});

function startCountdown(endTime, type) {
    function updateCountdown() {
        const now = new Date().getTime();
        const distance = endTime - now;

        if (distance > 0) {
            const days = Math.floor(distance / (1000 * 60 * 60 * 24));
            const hours = Math.floor((distance % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
            const minutes = Math.floor((distance % (1000 * 60 * 60)) / (1000 * 60));
            const seconds = Math.floor((distance % (1000 * 60)) / 1000);

            // Zaktualizuj odpowiednie elementy
            document.getElementById(`days_${type}`).innerHTML = days;
            document.getElementById(`hours_${type}`).innerHTML = hours;
            document.getElementById(`minutes_${type}`).innerHTML = minutes;
            document.getElementById(`seconds_${type}`).innerHTML = seconds;
        } else {
            // Kiedy czas minął
            document.getElementById(`days_${type}`).innerHTML = 0;
            document.getElementById(`hours_${type}`).innerHTML = 0;
            document.getElementById(`minutes_${type}`).innerHTML = 0;
            document.getElementById(`seconds_${type}`).innerHTML = 0;
            clearInterval(interval);
        }
    }

    const interval = setInterval(updateCountdown, 1000);
}

$(`[unique-script-id="w-w-dm-id"] .faq .for-flex`).click(function(event) {
  $(event.target).closest(".faq").toggleClass("active")
})

$(`[unique-script-id="w-w-dm-id"] .faq .toggle-faq-icon `).click(function(event) {
  event.stopPropagation();
  $(event.target).closest(".faq").toggleClass("active")
})

