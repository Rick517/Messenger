(function(){
    const chatId = location.pathname.split('/').pop();
    const socket = io(`/chat/${chatId}`);

    // Sockets are disconnected automatically when page closes. 
    // If you are using SPA, you don't close page. So you should
    // disconnect the socket manually
    if (Application.socket != undefined) {
        Application.socket.disconnect();
    }
    Application.socket = socket;

    const messagesContainer = document.getElementById('messages-container');
    const messageInput = document.getElementById('message-input');
    const submitMessage = document.getElementById('submit-message');
    const mainPersonContainer = document.getElementById('main');
    const scrollContainer = document.getElementById('scroll-container');

    //console.log('Chat socket is loaded. It is:', socket)

    var intervalId;
    let observedMessages = [];
    const observerOptions = {
        root: scrollContainer,
        threshold: 0  // observer doens't see my messages well enough
    }


    // TOKEN


    const create_token_loop = () => {
        let id = setInterval(() => {
            //console.log('Sending response to refresh tokens...')
            fetch('/refresh', {
                method: 'GET',
                Headers: {
                    'Content-Type': 'application/json',
                },
                credentials: 'same-origin'
            })
            .then(response => response.json())
            .then(data => {
                //console.log(data, 'This is the message from the client. ');
            })
            .catch(err => {
                //console.log(err);
            });
        }, 840000);
        return id;
    };



    // SOCKETS

    const handleAddingNewMessage = async (message, mine, isPrevMessageMine=false) => {
        //console.log('in handle message check mine', mine)
        if (!mine.length && isPrevMessageMine) {
            let lastMessage = messagesContainer.lastElementChild;
            ////console.log('last message', lastMessage);
            // Deleting avatar, but the container is preserved.
            let prevAvatar = lastMessage.querySelector('.little-avatar');
            prevAvatar.remove();
        }


        // One is like rounding numbers
        let isScrollAtBottom = scrollContainer.scrollTop + scrollContainer.clientHeight + 1 >= scrollContainer.scrollHeight;
        ////console.log('FSFDSFSD', isScrollAtBottom, scrollContainer.scrollTop, scrollContainer.scrollHeight, scrollContainer.clientHeight)
        messagesContainer.innerHTML += message;

        if (mine.length || isScrollAtBottom) {scrollToBottom(scrollContainer);}

        if (!mine.length) {
            observeMessage(messagesContainer.lastChild); 
        }
        
        // Await because of the bug with removing chat and updating its unseen messages count
        chatToTheTop(chatId);

        if (!mine.length) {
            //console.log('MINE', mine)
            updateUnseenMessagesCountUI(0, chatId, 1)
        }
    }

    socket.on('connect', (message) => {
        //console.log('Connected to the server: ' + chatId);
        //console.log('Message from server: ' + message);
        intervalId = create_token_loop();
    });

    socket.on('disconnect', () => {
        //console.log('Disconnected from the server. ');
        //console.log('Clearing the interval:');
        clearInterval(intervalId);
    });


    socket.on('add_new_message', (data) => {
        //console.log(data);
        let {message, mine, is_prev_message_mine: isPrevMessageMine} = data; // I send it from the socket, so rules are different than with pagination
        //console.log(message, mine)
        handleAddingNewMessage(message, mine, isPrevMessageMine);
    });



    // SUBMITTING MESSAGE


    //console.log('Creating listener for click of submittMessage...')
    submitMessage.addEventListener('click', () => {
        //console.log('Click on submitMessage button.')
        let message = messageInput.value;
        if (message.trim() !== "") {
            //console.log('Sending message:', message);
            messageInput.value = '';
            socket.emit('new_message', message);
        }
    });


    messageInput.onkeydown = (e) => {
        ////console.log('Received request to send message.', e.keyCode)
        if (e.keyCode === 13) {
            submitMessage.click();
        }
    }


    // UTILITIES

    async function chatToTheTop(chatId) {
        // Hope there is no other element with such id
        let chatElement = document.getElementById(chatId);
        if (chatElement && !(mainPersonContainer.firstElementChild === chatElement)) {
            //console.log('Moving a chat to the top...')
            // We risk to delete UI chat...
            chatElement.remove()
            mainPersonContainer.prepend(chatElement)
        }
    }


    // SEEING MESSAGES IN REAL TIME (ACTUALLY WHEN THEY ARE IN THE VIEWPORT OF YOUR PAGE)

    const messagesObserver = new IntersectionObserver((entries, observer) => {
        let messageTime = null;

        // Could be implemented binary search, but I don't think 
        // there are so many unseen messages in real time, so I won't
        entries.forEach(entry => {
            //console.log('CURRENT', entry)
            // isIntersecting means that it's in the view of the root container by threshold square
            if (entry.isIntersecting) {
                let messageNode = entry.target;
                let curTime = messageNode.getAttribute('data-message-time');
                //console.log('FOUND INTERSECTING MESSAGE', curTime);
                if (messageTime === null || curTime > messageTime) {
                    messageTime = curTime;
                    ////console.log('FINDING A TIME LARGER', messageTime);
                }
                // Shutting down observing current cluster of messages
                // Doing this because with diconnect I can't add new ones later
                messagesObserver.unobserve(messageNode)
            }
        })

        if (messageTime !== null) {
            setUpMessagesObserver(messageTime);
        }
    }, observerOptions)

    const requestSeeingMessages = async (chatId, messageTime) => {
        const response = await Application.gateway(
            // server handles
            {'chat_id': chatId, 'message_time': messageTime},
            '/seeing-messages',
            'application/json'
        )
        if (response.status === 200) {
            //console.log('Received seeing messages:', response.data)
            return response.data.count
        }
    }

    const observeMessage = (nodeMessage) => {
        // For scalability
        //console.log('Observing message:', nodeMessage)
        messagesObserver.observe(nodeMessage);
    }

    const updateUnseenMessagesCountUI = (count, chatId, dif=0) => {
        let leftChat = document.getElementById(chatId);
        let unseenMessagesSign = leftChat.querySelector('.unseen-messages-sign');
        //console.log(leftChat, unseenMessagesSign)

        if (count <= 0 && dif === 0) {
            unseenMessagesSign.textContent = '0';
            unseenMessagesSign.classList.add('display-none');
        } else {
            unseenMessagesSign.textContent = parseInt(unseenMessagesSign.innerHTML) + dif;
            unseenMessagesSign.classList.remove('display-none');
            //console.log('Updating unseen messages count.');
        }
    }

    // Note that these funcitons work in the cycle
    const setUpMessagesObserver = async (messageTime) => {
        let unseenCount = await requestSeeingMessages(chatId, messageTime);
        // When first iteration count will equal to zero, but
        // every time you new message is written, I will add new one
        // to be observed. After when user will have it in the viewport, 
        // new request sent to server and cycle stops again (or proceed
        // if messaging doesn't stop)
        // Anyway the purpose of seeing messages is to track seen and 
        // unseen ones during chat opened (and use this data). Otherwise
        // you won't know if user reads the messages or not. Or only by
        // requesting on opening chat to read all messages, but this is
        // slightly more limited and the main point - it is less scalable

        if (unseenCount > 0) {
            // You can do .reverse() but it takes O(n) to exclude one 
            // condition which takes O(n). So why?
            observedMessages = Array.from(messagesContainer.childNodes).slice(-unseenCount);
            //console.log('STARING MESSAGE OBSERVER', unseenCount, messagesContainer.childNodes)

            observedMessages.forEach(message => {
                observeMessage(message)  ;
            })
        }

        updateUnseenMessagesCountUI(unseenCount, chatId);
    }

    // current is to use current time (dealing on server)
    // you will probably change current on the timestamp given from server
    // when will want to open a chat from the position of last scrollbar position
    setUpMessagesObserver('current'); 
}());