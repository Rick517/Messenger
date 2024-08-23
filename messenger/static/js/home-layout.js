window.Application = {};


const popingContainer = document.getElementById('poping-info');
const popingText = popingContainer.querySelector('.poping-text');


const popInfo = (message) => {
    popingText.innerHTML = message;

    // Restart the animation
    popingContainer.classList.remove('poping-info-animation');
    void popingContainer.offsetWidth;
    popingContainer.classList.add('poping-info-animation');
}

// We return response from gateway and return error sign from sendFormData
async function gateway(data, url, contentType='application/json') {
    //console.log('Send request with axious.', data, url)
    // Response is json format automatically
    try {
        return await axios.post(
            url,
            data=data,
            {headers: {
                'Content-Type': contentType
            }}
        );
    } catch (e) {
        console.error('ERROR in gateway...\n', e)
        return e.response; // Imitating response.
    }
};


// One problem with searching: active chat isn't displayed
const handleGetChats = async (data, url, app, type='search') => {
    let response = await gateway(data, url, 'application/json');
    handleResponse(response, app, type);
}

const handleResponse = (response, app, type) => {
    //console.log('Getting chats from request', response, app)
    let status = response.status;
    if (status !== 200) {
        let error = response.data.error;
        console.error(error);
    } else {
        //console.log(response.data.chats);
        addPersonHTML(response.data.chats, app, type);
    }
    
    // TODO Learn and create flashing message 
    // TODO popover closing (by cancel function probably)
};


const generatePersonHTML = (chat, type) => {
    // TODO: I have did this in the beginning, but now I understand that generating html here
    // and in the jinga is not the rightest choice
    // I ams setting up types because we need to handle double ids on the dom and the html required is different.
    const pathRegex = /\/([^\/]+)(\/|$)/;
    let [, page] = location.pathname.match(pathRegex);

    if (type === 'search') {
        return `
        <div id=${chat.chat_id} class="person">
            <a class="chat-link" href="/${page}/${chat.chat_id}" data-routing-link>
                <img class="avatar" src="${chat.image}">
                <article>
                    <p class="name trancate">${chat.name}</p>
                    <p class="last-message">${chat.last_message.author}<span class="message trancate">${chat.last_message.message}</span></p>
                </article>
            </a>
        </div>
        `
    } else if (type === 'forward') {
        // I don't wanna the messenger to redirect to the chat on click. I have removed the href.
        return `
        <div id="forward-${chat.chat_id}" class="person">
            <a class="chat-link">
                <img class="avatar" src="${chat.image}">
                <article>
                    <p class="name">${chat.name}</p>
                </article>
            </a>
        </div>
        `
    }

    
    return html;
}

const addPersonHTML = (chats, app, type) => {
    let html = "";
    for (let chat of chats) {
        //console.log('CURRENT', chat)
        html += generatePersonHTML(chat, type);
    }
    //console.log(html, app, type)
    app.innerHTML = html;
}

const sendFormData = async (formData, url, contentType) => {
    let data = Object.fromEntries(formData.entries());
    let response = await gateway(data, url, contentType);
    if (response.status !== 201) {
        //console.log('The error from submit button:', response);
        popInfo(response.data.error)
        return true;
    }

    return;
}

// COPYING

const handleCopy = (text) => {
    navigator.clipboard.writeText(text);
}


// Why don't I use import? Module files are laoded ones and in one scope
// Thus routing stuff - rendering html views is fully restricted
// The only downside is being able to access the data everywhere. Thus we use an object: Application.
Application.sendFormData = sendFormData;
Application.popInfo = popInfo;
Application.handleCopy = handleCopy;
Application.handleGetChats = handleGetChats;
Application.gateway = gateway;
