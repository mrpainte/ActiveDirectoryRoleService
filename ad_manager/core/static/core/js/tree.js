/**
 * OU tree lazy-loading via htmx.
 * When a tree node is clicked, fetch children from the server and toggle visibility.
 */
document.addEventListener('DOMContentLoaded', function () {
    document.body.addEventListener('click', function (e) {
        var toggle = e.target.closest('.tree-toggle');
        if (!toggle) return;

        e.preventDefault();
        var node = toggle.closest('.tree-node');
        if (!node) return;

        var childrenContainer = node.nextElementSibling;

        // If children already loaded, just toggle visibility
        if (childrenContainer && childrenContainer.classList.contains('tree-children')) {
            if (childrenContainer.style.display === 'none') {
                childrenContainer.style.display = '';
                toggle.textContent = '\u25BC';
            } else {
                childrenContainer.style.display = 'none';
                toggle.textContent = '\u25B6';
            }
            return;
        }

        // Lazy-load children via htmx
        var dn = node.getAttribute('data-dn');
        if (!dn) return;

        var url = '/directory/ous/children/?dn=' + encodeURIComponent(dn);

        var container = document.createElement('div');
        container.className = 'tree-children';
        node.parentNode.insertBefore(container, node.nextSibling);

        toggle.textContent = '\u25BC';

        htmx.ajax('GET', url, {
            target: container,
            swap: 'innerHTML'
        });
    });
});
