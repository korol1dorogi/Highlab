/* =========================================================
   Магазин — единый клиентский скрипт.
   Корзина (AJAX), уведомления, ленивая загрузка изображений.
   ========================================================= */
(function () {
    'use strict';

    /* ---------- Счётчик корзины ---------- */
    function updateCartBadge(totalQuantity) {
        document.querySelectorAll('.cart-badge').forEach(function (badge) {
            badge.textContent = totalQuantity;
            badge.setAttribute('data-count', totalQuantity);
        });
    }
    window.updateCartBadge = updateCartBadge;

    /* ---------- Уведомления ---------- */
    function showNotification(message, type) {
        type = type || 'success';

        var path = window.location.pathname;
        if (path.includes('cart') || path.includes('checkout')) { return; }

        var container = document.getElementById('notification-container');
        if (!container) {
            container = document.createElement('div');
            container.id = 'notification-container';
            container.className = 'notification-container';
            document.body.appendChild(container);
        }

        var icons = {
            success: 'bi-cart-check-fill',
            danger: 'bi-exclamation-triangle-fill',
            info: 'bi-info-circle-fill'
        };
        var title = type === 'success' ? 'Добавлено' : (type === 'danger' ? 'Внимание' : 'Инфо');

        var note = document.createElement('div');
        note.className = 'custom-notification ' + type;
        note.innerHTML =
            '<div class="d-flex align-items-center p-3">' +
                '<div class="notification-icon"><i class="bi ' + (icons[type] || icons.info) + '"></i></div>' +
                '<div class="notification-content"><strong class="me-1">' + title + '.</strong> ' + message + '</div>' +
                '<button type="button" class="notification-close" aria-label="Закрыть">' +
                    '<i class="bi bi-x"></i></button>' +
            '</div>';

        note.querySelector('.notification-close').addEventListener('click', function () {
            note.remove();
        });

        container.appendChild(note);
        requestAnimationFrame(function () { note.classList.add('show'); });

        if (type === 'success') {
            var cartIcon = document.querySelector('.shop-cart-btn i.bi-cart, .shop-cart-btn i.bi-cart3');
            if (cartIcon) {
                cartIcon.classList.add('cart-bounce');
                setTimeout(function () { cartIcon.classList.remove('cart-bounce'); }, 600);
            }
        }

        setTimeout(function () {
            note.style.opacity = '0';
            note.style.transform = 'translateX(420px)';
            setTimeout(function () { note.remove(); }, 300);
        }, 2500);
    }
    window.showNotification = showNotification;

    /* ---------- AJAX добавление в корзину ---------- */
    async function handleAddToCart(e) {
        e.preventDefault();
        var form = this;
        var submitBtn = form.querySelector('button[type="submit"]');
        var originalHtml = submitBtn ? submitBtn.innerHTML : '';

        if (submitBtn) {
            submitBtn.innerHTML = '<i class="bi bi-arrow-repeat spinner"></i> Добавляем…';
            submitBtn.disabled = true;
        }

        try {
            var response = await fetch(form.action, {
                method: 'POST',
                body: new FormData(form),
                headers: { 'X-Requested-With': 'XMLHttpRequest' }
            });

            if (response.ok) {
                var result = await response.json();
                if (result.success) {
                    updateCartBadge(result.total_quantity);
                    showNotification(result.message || 'Товар в корзине', 'success');
                } else {
                    showNotification(result.message || 'Не удалось добавить', 'danger');
                }
            } else {
                form.submit();
            }
        } catch (err) {
            showNotification('Ошибка соединения. Попробуйте ещё раз.', 'danger');
        } finally {
            if (submitBtn) {
                submitBtn.innerHTML = originalHtml;
                submitBtn.disabled = false;
            }
        }
    }

    /* ---------- Ленивая загрузка изображений ---------- */
    function initLazyLoading() {
        var lazyImages = document.querySelectorAll('img[data-src]');
        if (!lazyImages.length) { return; }

        function loadImage(img) {
            if (!img.dataset.src) { return; }
            img.src = img.dataset.src;
            img.addEventListener('load', function () {
                img.classList.remove('lazy-load-placeholder');
                img.classList.add('loaded');
            });
            img.removeAttribute('data-src');
        }

        if (!('IntersectionObserver' in window)) {
            lazyImages.forEach(loadImage);
            return;
        }

        var observer = new IntersectionObserver(function (entries, obs) {
            entries.forEach(function (entry) {
                if (entry.isIntersecting) {
                    loadImage(entry.target);
                    obs.unobserve(entry.target);
                }
            });
        }, { rootMargin: '100px', threshold: 0.01 });

        lazyImages.forEach(function (img) { observer.observe(img); });
    }

    /* ---------- Инициализация ---------- */
    document.addEventListener('DOMContentLoaded', function () {
        if (!window.location.pathname.includes('cart')) {
            document.querySelectorAll('.add-to-cart-form').forEach(function (form) {
                form.addEventListener('submit', handleAddToCart);
            });
        }
        initLazyLoading();
    });
})();
