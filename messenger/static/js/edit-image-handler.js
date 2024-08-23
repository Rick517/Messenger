(function(){
    const fileInput = document.getElementById('profile-file-input');
    const imageWrapper = document.getElementById('profile-image-wrapper');

    fileInput.addEventListener('change', (event) => {
        // Using blob instead of file reader because it should be savier for CSP requests.
        // And it is easier to do.
        const file = event.target.files[0];
        const url = URL.createObjectURL(file);
        imageWrapper.style.backgroundImage = `url(${url})`;
    });
}());