(function() {
    const submitButton = document.querySelector('.edit-chat-submit');
    const form = document.querySelector('#edit-chat-form');
    const fileInput = document.getElementById('chat-file-input');
    const imageWrapper = document.getElementById('chat-image-wrapper');

    submitButton.addEventListener('click', async (e) => {
        //console.log('Submit form to edit chat is clicked.')
        e.preventDefault(); 
        const chat_id = Application.getChatIdFromPathname(location.pathname);
        const url = "/view/edit_chat/" + chat_id
        let formData = new FormData(form);
        let error = await Application.sendFormData(formData, url, 'multipart/form-data');
        if (!error) {
            Application.router(); // updating everything because the data is changed in many places
            Application.popInfo('The data was updated. ')
        }
    });

    fileInput.addEventListener('change', (event) => {
        const file = event.target.files[0];
        const url = URL.createObjectURL(file);
        imageWrapper.style.backgroundImage = `url(${url})`;
    });

})();