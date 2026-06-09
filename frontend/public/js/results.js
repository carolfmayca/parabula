document.addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll('.interaction-row .details-link').forEach(function (btn) {
        btn.addEventListener('click', function () {
            const targetId = btn.getAttribute('data-target');
            const panel = document.getElementById(targetId);
            const arrow = btn.querySelector('.details-arrow');
            if (!panel) return;
            const isOpen = panel.classList.contains('open');

            // Fechar todos os outros painéis abertos
            document.querySelectorAll('.interaction-detail-panel.open').forEach(function (p) {
                p.classList.remove('open');
            });
            document.querySelectorAll('.details-link.active').forEach(function (b) {
                b.classList.remove('active');
                const a = b.querySelector('.details-arrow');
                if (a) a.textContent = '▾';
            });

            if (!isOpen) {
                panel.classList.add('open');
                btn.classList.add('active');
                if (arrow) arrow.textContent = '▴';
            }
        });
    });
});
