// SCROLLBAR

function scrollToBottom(scrollContainer, position=null) {
    scrollContainer.style.scrollBehavior = 'auto';
    if (position != null) {
        scrollContainer.scrollTop = position;
    } else {
        scrollContainer.scrollTop = scrollContainer.scrollHeight;
    }
    
    scrollContainer.style.scrollBehavior = 'smooth';
}


(function(){
    //console.log('Chat js has been loaded.')
    // Be cautios with naming things because several files could intersect.
    const chatId = location.pathname.split('/').pop();

    const scrollContainer = document.getElementById('scroll-container');
    const messagesContainer = document.getElementById('messages-container');
    const messagePopover = document.getElementById('message-popover');
    const buttonMessagePopover = document.getElementById('btn-message-popover');
    const buttonForwardPopover = document.getElementById('btn-forward-popover');
    const forwardPopover = document.getElementById('forward-popover');
    const forwardOptions = forwardPopover.querySelector('#forward-options');
    const forForwardContainer = forwardPopover.querySelector('#for-forward-container');
    const forwardSearch = forwardPopover.querySelector('#forward-search');
    const forwardPopoverCloseButton = forwardPopover.querySelector('#forward-popover-close');
    const blockUserButton = document.getElementById('block-user');
    const deleteChatButton = document.getElementById('delete-chat-button');
    const openEditChatLink = document.getElementById('open-edit-chat');
    const closeSettingsButton = document.getElementById('close-settings');
    const settingsButton = document.getElementById('settings-button');
    const chatSettingsPopover = document.getElementById('chat-settings');

    const buttonWidth = settingsButton.offsetWidth;
    const popoverWidth = 152; // There is no other way to calculate the width of the html popover...
    const closeLeft = document.getElementById('close-left');
    let isLoading = false; // Controls refusing to refetch cuz of scorlling listener
    let pageNumber = 0;
    

    // PAGINATION 

    const fetchMessages = async (chatId, pageNumber) => {
        return await fetch("/chat/pagination?" + `chatId=${chatId}&pageNumber=${pageNumber}`, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
            },
            credentials: 'include'
        })
        .then(response => {
            if (!response.ok) {throw (new Error(response.message))}
            return response.json();
        })
        .then(data => {return data})
        .catch(err => {
            ////console.log('Error fetching pagination form server.', err);
            return [];
        })
    }


    const handlePagination = async (chatId) => {
        ////console.log(chatId, pageNumber);
        const messagesHTML = await fetchMessages(chatId, pageNumber);

        if (messagesHTML == "") {
            return true; // maximum scrolling
        }

        ////console.log(messagesHTML)

        messagesContainer.innerHTML = messagesHTML + messagesContainer.innerHTML;
        pageNumber++; // Incrementing count of current messages displayed
    }

    scrollContainer.addEventListener('scroll', async () => {
        // Checking if user scrolled to the end of the container
        // If it is, we fetch more messages
        // If there is no more messages nothing happens
        ////console.log('Messages scrolling, sign:', scrollContainer.scrollTop)
        if (scrollContainer.scrollTop < 300 && !isLoading) {
            let initialScrollFraction = scrollContainer.scrollTop / scrollContainer.scrollHeight;
            isLoading = true;
            const maximumScrolling = await handlePagination(chatId);
            
            if (!maximumScrolling) {
                // It is always placed about four times, though that's bad measure
                // because size of messages differ
                // 2 because it's slightly better this way
                let position = scrollContainer.scrollHeight * initialScrollFraction * 2;
                scrollToBottom(scrollContainer, position)

                // Timeout to prevent instant messages delivering
                // Note that we don't toggle isloading now.
                // It will stop any further loading of messages.
                setTimeout(() => {isLoading = false}, 50); 
            }
        }
    })

    const setUp = async () => {
        await handlePagination(chatId) // first set up
        scrollToBottom(scrollContainer)
    }

    setUp();


    // MESSAGE FUNCTIONS 

    var messageId;

    const closePopover = (button) => {
        messageId = null;
        button.popoverTargetAction = 'hide';
        button.click();
        button.popoverTargetAction = 'show';
    }

    messagesContainer.addEventListener('contextmenu', e => {
        e.preventDefault();
        //console.log('Messages container contextmenu is clicked', e.clientX, e.clientY)

        messageId = e.target.id; 
        messagePopover.style.top = e.clientY + 'px'
        messagePopover.style.left = e.clientX + 'px'
        buttonMessagePopover.click();
        messagePopover.popover = 'auto';

        return false; // prevent right click default action
    })

    messagePopover.addEventListener('click', (e) => {
        if (messageId == null) {return}
        let messageElement = document.getElementById(messageId);
        //console.log(messageElement);
        switch (e.target.id) {
            case "copy-text-button":
                //console.log('Copy text button is clicked.')
                Application.handleCopy(
                    messageElement.querySelector('.message-text').innerHTML
                );
                Application.popInfo('Message was copied!');
                return closePopover(buttonMessagePopover);
            case "delete-button":
                //console.log('Delete button is clicked.')
                // Can anyone authenticated delete any message this way? Maybe, cors prevents?
                fetch("/message-functions?" + `chat_id=${chatId}&&message_id=${messageId}`, {
                    method: 'DELETE'
                }).then(
                    response => {
                        if (response.ok) {
                            messageElement.remove();
                            Application.popInfo('Message was deleted.');
                        }
                    }
                )
                return closePopover(buttonMessagePopover);
            case "forward-button":
                initForwardPopover(messageId);
                return closePopover(buttonMessagePopover);
            default:
                //console.log('Invalid action:', e.target.id);
        }
    })

    const initForwardPopover = async (messageId) => {
        //console.log('Initializing forwarding popover...')
        // TODO: check search.
        // The problem with coping: every chat has DOM id which I can't jsut copy and paste.
        // However I can do this here because it is a popover which will be closed on the click outside.
        // The inner htmls will be overwritten next time they will be accessed.
        await handleAddingSearchChats("")
        forForwardContainer.innerHTML = messageId;
        buttonForwardPopover.click();
    }

    const handleForwarding = async (e) => {
        let curMessageId = forForwardContainer.innerHTML;
        //console.log(chatId, curMessageId)
        let forwardChat = e.target.parentNode;

        let forwardTo = forwardChat.id.slice(start=8);
        //console.log('Handling forwarding', forwardChat, forwardTo)

        // Overkill but reusing
        let formData = new FormData();
        formData.append('chat_id', chatId);
        formData.append('message_id', curMessageId);
        formData.append('forward_to', forwardTo);

        const error = await Application.sendFormData( // Gateway method request is post.
            formData,
            "/message-functions",
            'multipart/form-data'
        )

        if (error == undefined) {
            // Adding new message into the current chat if it is forward to.
            // The problem is we need to generate html for this. Thus to do it from the server. Thus to send it in response instead of error. Thus modifying many functions.
            // Current solution is just that a man either should not to send email into the current chat or he needs to refresh it.
            /*if (chatId === forwardTo) {
                let message = document.getElementById(curMessageId).querySelector('.text').innerHTML;
                handleAddingNewMessage(message, "mine")
            }*/
            Application.popInfo('Message was forwarded.');
        }

        closePopover(buttonForwardPopover);
    }

    const handleAddingSearchChats = async (query) => {
        await Application.handleGetChats(
            query,
            "/search/group", 
            forwardOptions, // where to put
            type='forward'
        )

        //console.log('The chats for forward are gotten. ')
    }

    forwardOptions.addEventListener('click', e => handleForwarding(e)); // Preventing compounding listeners. That's why here.

    forwardSearch.addEventListener('keyup', () => {
        let query = forwardSearch.value;
        //console.log('Searching from forward:', query);
        handleAddingSearchChats(query);
    });

    forwardPopoverCloseButton.addEventListener('click', () => {closePopover(buttonForwardPopover);});


    /* CHAT FUNCTIONS */

    settingsButton.addEventListener('click', () => {
        // How to get a distance from a random button to the right of the window?
            // To get to the rigth or the bottom you need to subtract from full width/height.
        let distanceLeft = settingsButton.getBoundingClientRect().left;
        chatSettingsPopover.style.left = (distanceLeft + buttonWidth - popoverWidth)  + 'px';
    });

    const fetchChatFunctions = async (chatId, method) => {
        const response = await fetch('/chat-functions?chat_id=' + chatId, {
            method: method
        });

        return response
    }

    if (blockUserButton != undefined) {
        blockUserButton.addEventListener('click', async () => {
            //console.log('Blocking user');
    
            const response = await fetchChatFunctions(chatId, 'GET');
            //console.log(response);
            if (response.status === 200) {
                Application.router(toRender=[false, true]); 
            } 
    
            closeSettingsButton.click();
        });
    }

    openEditChatLink.addEventListener('click', () => {
        closeSettingsButton.click();
    });

    deleteChatButton.addEventListener('click', async () => {
        //console.log('Deleting chat'); 

        const response = await fetchChatFunctions(chatId, 'DELETE');

        //console.log(response);
        if (response.status === 202) {
            let url = location.pathname.match(Application.pageRegex)[1];
            Application.navigate(`/${url}`, toRender=[true, true]); 
        }
    });


    /* TOGGLING LEFT */

    if (closeLeft) {
        closeLeft.addEventListener('click', () => {
            let leftContainer = document.getElementById('left');
            let curDisplay = leftContainer.style.display;
            
            if (curDisplay !== 'none') {
                leftContainer.style.display = 'none';
                closeLeft.innerHTML = '<i class="fa-solid fa-bars"></i>';
            } else {
                leftContainer.style.display = 'initial';
                closeLeft.innerHTML = '<i class="fa-solid fa-arrow-left-long"></i>';
            }
        });
    }

})();

