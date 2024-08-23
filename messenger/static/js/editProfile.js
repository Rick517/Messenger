(function() {
    const submitButton = document.querySelector('.edit-profile-submit');
    const form = document.querySelector('#edit-profile-form');

    submitButton.addEventListener('click', async (e) => {
        //console.log('Submit form to edit profile is clicked.')
        e.preventDefault(); 
        const url = "/view/profile"
        let formData = new FormData(form);
        let error = await Application.sendFormData(formData, url, 'multipart/form-data');
        if (!error) {
            Application.router(toRender=[true, false]) // update the current user's data on the page
            Application.popInfo('The data was updated. ')
        }
    });
})();