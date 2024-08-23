(function() {
    // TODO: chats aren't generated after appending new one
    //console.log('Contacts.js is loaded. ');

    const email = document.getElementById('email');
    const firstName = document.getElementById('first_name');
    const doneBtn = document.getElementById('done-btn-wrapper');
    const cancelButton = document.getElementById('cancel-btn');
    const addUserPopover = document.getElementById('add-user-popover');
    
    const submitButton = document.getElementById('submit');
    const form = document.getElementById('form');
    const search = document.getElementById('search');
    const main = document.getElementById('main');

    // POPOVER

    // Adding active class to the done button

    const checkFilledInputs = () => {
        if (email.value && firstName.value) {
            doneBtn.classList.add('active-btn');
        } else {
            doneBtn.classList.remove('active-btn');
        }
    };

    email.addEventListener('keyup', () => {
        checkFilledInputs();
    });

    firstName.addEventListener('keyup', () => {
        checkFilledInputs();
    });

    cancelButton.addEventListener('click', () => {
        //console.log('Cancelling.')
        addUserPopover.popover = "manual";
        cancelButton.click();
        addUserPopover.popover = "auto";
    });



    // FETCHING FORM

    submitButton.addEventListener('click', async (e) => {
        e.preventDefault();
        //console.log('Submitting form from contacts...', e.target);
        // TODO handle crsf token
        const error = await Application.sendFormData(
            new FormData(form),
            "/view/contacts",
            "application/json"
        );

        if (error == null) {
            Application.handleGetChats("", '/search/contacts', main);
        }
        
        cancelButton.click();
    });


    // SEARCHING FOR CONTACTS

    search.addEventListener('keyup', () => {
        let query = search.value;
        //console.log('Searching:', query);
        Application.handleGetChats(query, '/search/contacts', main)
    })



})();
