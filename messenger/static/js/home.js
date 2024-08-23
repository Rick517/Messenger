
// Using a router with replacing html the previous listeners, functions and variables stay in the source of the page. They devour performance and create interuptions.
// I don't clean up the listeners because I hope that they are removed when the html elements are completely removed on replacing html.
// I think they are actually removed because the listener for penContainer doesn't work (id is the same)

(function() {
    //console.log('Home.js is loaded.');

    const penContainer = document.getElementById('pen-container-click');
    const bar = document.getElementById('bar');
    const penActionsTooptip = document.getElementById('actions');
    const xmark = document.getElementById('xmark');
    const pen = document.getElementById('pen');
    const search = document.getElementById('search');
    const main = document.getElementById('main');
    const doneGroupButtonContainer = document.getElementById('done-group-button-container');
    const addGroupPopover = document.getElementById('add-group-popover');
    const actionsContainer = document.getElementById('actions');
    const groupRequiredInputs = [addGroupPopover.querySelector('#group-name-input')];
    const doneBugButton = document.getElementById('done-btn-wrapper');
    const cancelButton = document.getElementById('cancel-btn');
    const reportBugPopover = document.getElementById('report-bug-popover');
    const bugRequiredInputs = reportBugPopover.querySelectorAll('.input-field'); 
    const bugForm = document.getElementById('report-bug-form');
    const groupForm = document.getElementById('group-form');
    const groupNameInput = document.getElementById('group-name-input');


    // PEN CONTAINER

    let sign = true;
    const switchBarDisplay = () => {
        // Elements are accessed here because something goes wrong with downloading them at the beginning of the file (they become old)
        const sidebar = document.getElementById('sidebar');
        sidebar.style.display = sign ? 'inherit' : 'none';
        sign = !sign;
    }

    let penSign = true;
    const switchPenDisplay = () => {
        if (penSign) {
            pen.style.display = 'none';
            xmark.style.display = 'initial';
            penActionsTooptip.style.display = 'inherit';
        } else {
            pen.style.display = 'initial';
            xmark.style.display = 'none';
            penActionsTooptip.style.display = 'none';
        }
        penSign = !penSign;
    }

    penContainer.addEventListener('click', () => {
        //console.log('Pen clicked');
        switchPenDisplay();
    });

    bar.addEventListener('click', () => {
        //console.log('Bar clicked');
        switchBarDisplay();
    });


    // SEARCHING FOR CONTACTS

    search.addEventListener('keyup', () => {
        let query = search.value;
        //console.log('Searching:', query);
        Application.handleGetChats(query, '/search/group', main);
    });


    // PEN CONTAINER FUNCTIONS

    actionsContainer.addEventListener('click', (e) => {
        //console.log('Action clicked:', e.target.id);
        switch (e.target.id) {
            case "new-group":
                return
            case "new-contact":
                Application.navigate()
                return
            case "new-message":
                switchPenDisplay();
                search.focus();
                return
            case 'cancel-group':
                closeAddGroupPopover();
                return
            case 'done-group-button':
                // Note that I use submit - not button. 
                // Though I don't think it was the rightest choice back then
                handleGroupSubmit(e);
                return
            default:
                //console.log('Invalid action:', e.target.id);
        }
    });

    groupNameInput.addEventListener('keyup', () => {
        checkFilledInputs(groupRequiredInputs, doneGroupButtonContainer);
    })


    // POPOVER

    const checkFilledInputs = (inputs, doneButton) => {
        ////console.log('Checking filled inputs.')
        for(let inp of inputs) {
            ////console.log('INPUT VALUE', inp, inp.value == undefined, inp.value.length)
            if (!inp.value.length) {
                ////console.log('Inputs are still not completed.')
                doneButton.classList.remove('active-btn');
                return;
            }
        }

        //console.log('Inputs could be added. ')
        doneButton.classList.add('active-btn');
    };

    for (let inp of bugRequiredInputs) {
        inp.addEventListener('keyup', () => {
            checkFilledInputs(bugRequiredInputs, doneBugButton);
        });
    }

    const closePopover = (target, popover) => {
        //console.log('Cancelling.')
        popover.popover = "manual";
        cancelButton.popovertarget = target;
        cancelButton.click();
        popover.popover = "auto";
    }

    cancelButton.addEventListener('click', () => {
        closePopover('report-bug-popover', reportBugPopover);
    });

    doneBugButton.addEventListener('click', async (e) => {
        const callback = () => {
            cancelButton.click();
            Application.popInfo('The bug is reported. Thanks!');
        }
        handleSubmit(e, bugForm, "/report-bug", "multipart/form-data", callback);
    });

    const handleGroupSubmit = (e) => {
        const callback = () => {
            closeAddGroupPopover();
            Application.handleGetChats("", '/search/group', main);
        }
        handleSubmit(e, groupForm, "/view/home", "multipart/form-data", callback);      
    };

    const handleSubmit = async (event, form, url, contentType, callback) => {
        event.preventDefault();

        const error = await Application.sendFormData(
            new FormData(form),
            url,
            contentType
        );

        if (error == null) {
            callback();
        }
    }

    const closeAddGroupPopover = () => {
        //console.log('Cancelling group form.')
        closePopover('add-group-popover', addGroupPopover);
    }
    
})();