/**
 * Happy Child School – shared UI: Toastr, SweetAlert2, DataTables
 */
(function () {
    'use strict';

    const TAG_MAP = {
        debug: 'info',
        info: 'info',
        success: 'success',
        warning: 'warning',
        error: 'error',
    };

    function initToastr() {
        if (typeof toastr === 'undefined') return;
        toastr.options = {
            closeButton: true,
            progressBar: true,
            positionClass: 'toast-top-right',
            timeOut: 5000,
            extendedTimeOut: 2000,
        };
        document.querySelectorAll('[data-django-message]').forEach(function (el) {
            const tags = el.dataset.djangoMessage || 'info';
            const text = el.textContent.trim();
            if (text) {
                toastr[TAG_MAP[tags] || 'info'](text);
            }
        });
    }

    function initDataTables() {
        if (typeof $ === 'undefined' || !$.fn.DataTable) return;
        document.querySelectorAll('table.datatable').forEach(function (table) {
            if ($.fn.DataTable.isDataTable(table)) return;
            const noSort = table.dataset.noSort;
            const columnDefs = noSort
                ? [{ orderable: false, targets: parseInt(noSort, 10) }]
                : [];
            $(table).DataTable({
                responsive: true,
                pageLength: 25,
                lengthMenu: [[10, 25, 50, 100, -1], [10, 25, 50, 100, 'All']],
                order: [],
                columnDefs: columnDefs,
                language: {
                    search: 'Search:',
                    lengthMenu: 'Show _MENU_ entries',
                    info: 'Showing _START_ to _END_ of _TOTAL_ entries',
                    emptyTable: 'No records found',
                    zeroRecords: 'No matching records found',
                },
            });
        });
    }

    function initDeleteLinks() {
        if (typeof Swal === 'undefined') return;
        document.querySelectorAll('a[data-swal-delete]').forEach(function (link) {
            link.addEventListener('click', function (e) {
                e.preventDefault();
                const href = link.getAttribute('href');
                Swal.fire({
                    title: link.dataset.swalTitle || 'Are you sure?',
                    text: link.dataset.swalText || 'This action cannot be undone.',
                    icon: 'warning',
                    showCancelButton: true,
                    confirmButtonColor: '#dc3545',
                    cancelButtonColor: '#6c757d',
                    confirmButtonText: 'Yes, delete it',
                    cancelButtonText: 'Cancel',
                }).then(function (result) {
                    if (result.isConfirmed) {
                        window.location.href = href;
                    }
                });
            });
        });
    }

    function initConfirmForms() {
        if (typeof Swal === 'undefined') return;
        document.querySelectorAll('form.swal-confirm-form').forEach(function (form) {
            form.addEventListener('submit', function (e) {
                e.preventDefault();
                const title = form.dataset.swalTitle || 'Confirm action';
                const text = form.dataset.swalText || 'Are you sure you want to proceed?';
                Swal.fire({
                    title: title,
                    text: text,
                    icon: 'warning',
                    showCancelButton: true,
                    confirmButtonColor: '#dc3545',
                    cancelButtonColor: '#6c757d',
                    confirmButtonText: 'Yes, confirm',
                    cancelButtonText: 'Cancel',
                }).then(function (result) {
                    if (result.isConfirmed) {
                        form.classList.remove('swal-confirm-form');
                        HTMLFormElement.prototype.submit.call(form);
                    }
                });
            });
        });
    }

    function initActionConfirms() {
        if (typeof Swal === 'undefined') return;
        document.querySelectorAll('[data-swal-confirm]').forEach(function (el) {
            el.addEventListener('click', function (e) {
                e.preventDefault();
                const href = el.getAttribute('href') || el.dataset.href;
                Swal.fire({
                    title: el.dataset.swalTitle || 'Confirm',
                    text: el.dataset.swalText || '',
                    icon: el.dataset.swalIcon || 'question',
                    showCancelButton: true,
                    confirmButtonText: 'Yes',
                    cancelButtonText: 'Cancel',
                }).then(function (result) {
                    if (result.isConfirmed && href) {
                        window.location.href = href;
                    }
                });
            });
        });
    }

    function getCsrfToken() {
        const meta = document.querySelector('meta[name="csrf-token"]');
        if (meta && meta.content) return meta.content;
        const match = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/);
        return match ? decodeURIComponent(match[1]) : '';
    }

    function initCsrfProtection() {
        const token = getCsrfToken();
        if (!token) return;

        const originalFetch = window.fetch;
        window.fetch = function (input, init) {
            init = init || {};
            const method = ((init.method || 'GET') + '').toUpperCase();
            if (method !== 'GET' && method !== 'HEAD' && method !== 'OPTIONS' && method !== 'TRACE') {
                init.headers = new Headers(init.headers || {});
                if (!init.headers.has('X-CSRFToken')) {
                    init.headers.set('X-CSRFToken', getCsrfToken());
                }
            }
            return originalFetch.call(this, input, init);
        };

        if (typeof $ !== 'undefined' && $.ajaxSetup) {
            $.ajaxSetup({
                beforeSend: function (xhr, settings) {
                    const m = (settings.type || 'GET').toUpperCase();
                    if (!/^(GET|HEAD|OPTIONS|TRACE)$/i.test(m)) {
                        xhr.setRequestHeader('X-CSRFToken', getCsrfToken());
                    }
                },
            });
        }
    }

    document.addEventListener('DOMContentLoaded', function () {
        initCsrfProtection();
        initToastr();
        initDataTables();
        initDeleteLinks();
        initConfirmForms();
        initActionConfirms();
    });
})();