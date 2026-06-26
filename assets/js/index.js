document.addEventListener('DOMContentLoaded', function () {
    const imageModalElement = document.getElementById('imageModal');
    const modalImage = document.getElementById('modalImage');
    const bsModal = new bootstrap.Modal(imageModalElement);

    // Close modal on any click
    imageModalElement.addEventListener('click', function () {
        bsModal.hide();
    });

    document.querySelectorAll('.img-thumbnail-custom').forEach(img => {
        img.addEventListener('click', function () {
            modalImage.src = this.src;
            modalImage.alt = this.alt;
            bsModal.show();
        });
    });
});