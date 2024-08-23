(function(){
    const addMembersContainer = document.getElementById('add-members-container');
    const closeButton = document.getElementById('close-add-members');
    const addUsersButton = document.getElementById('add-users-button');

    const closeContainer = () => {
        addMembersContainer.remove();
    }
    
    closeButton.addEventListener('click', () => {
        closeContainer();
    });

    addUsersButton.addEventListener('click', async () => {
        const users = addMembersContainer.querySelectorAll('.person');
        const data = [];
        ////console.log(users)
        for (let user of users) {
            const checkbox = user.querySelector('input[type="checkbox"]');
            if (checkbox.checked) {
                const id = user.getAttribute('data-peer-id');
                ////console.log(`User ${id} added.`);
                data.push(parseInt(id));
            }
        }

        //console.log(data)
        if (data.length > 0) {
            const chat_id = Application.getChatIdFromPathname(location.pathname);
            await Application.gateway(
                JSON.stringify(data),
                '/view/add-members/' + chat_id,
                'application/json'
            )
            Application.router([false, true]);
        }
    });

}());