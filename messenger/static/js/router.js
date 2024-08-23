import Contacts from "./views/Contacts.js";
import EditProfile from "./views/EditProfile.js";
import Settings from "./views/Settings.js";
import Home from "./views/Home.js";
import Chat from "./views/Chat.js";
import ChatProfile from "./views/ChatProfile.js";
import EditChat from "./views/EditChat.js";
import AddMembers from "./views/AddMembers.js";

(function(){
    const left = document.getElementById('left');
    const right = document.getElementById('right');
    const chatRegex = /^\/[a-z]+\/(-?[0-9]{10}$)/;
    const head = document.head;
    const phoneViewportWidth = 426;

    // first word after flash of any lenght > 0 and second slash is optional \
        // (first chatRegex require second slash, so everything is okay)
    const pageRegex = /\/([^\/]+)\/?/; 

    const getChatIdFromPathname = (pathname) => {
        //console.log('SDFSDFSDFSD', pathname.match(chatRegex)[1])
        return pathname.match(chatRegex)[1]
    }

    const getPageNameFromPathname = (pathname) => {
        //console.log('SDFSDFSDFSD', pathname.match(pageRegex)[1])
        return pathname.match(pageRegex)[1]
    }

    const getViewChatId = (curPath1, curPath2=null) => {
        if (curPath2 === null) {curPath2 = curPath1};
        let [, page] = curPath1.match(pageRegex);
        let possibleId = curPath2.match(chatRegex);
        let id = (possibleId !== null ? possibleId[1] : null);
        //console.log(page, id)
        return [ page, id ];
    }

    const loadAppScripts = (app) => {
        const scriptTags = app.querySelectorAll('script');
        //console.log('Scripts to laod are', scriptTags)
        scriptTags.forEach(script => {
            const newScript = document.createElement('script');
            if (script.src) {
                newScript.src = script.src;
            } else {
                newScript.innerHTML = script.innerHTML;
            }
            //newScript.type = "module";
            script.remove();
            app.appendChild(newScript);
            //console.log('New script:', newScript)
        });
    }

    const loadCSSFiles = (source) => {
        const cssFiles = source.querySelectorAll('link[rel="stylesheet"]');
        //console.log('CURRENT CSS files to load are', cssFiles);
        cssFiles.forEach(file => {
            let fileId = file.id;
            file.remove(); // actually removing from the app
            //console.log(file, fileId)
            if (head.querySelector(`#${fileId}`) == undefined) {
                head.appendChild(file);
            }
        })
    }

    const loadViewHTML = async (view, app, loadButtons=true) => {
        //extinguishPreviousScripts(app);

        ////console.log('Adjusting app html. The path is:', curPath, 'The match class is:', view);
        let result = await view.getHTML()

        ////console.log('Resulted html is', result);
        app.innerHTML = result;
        
        loadAppScripts(app);
        loadCSSFiles(app);

        // Condition for circular loading from button router request.
        if (loadButtons) {displayFromStorage('openedButtonViews')};
    }

    const removeActiveChatStyle = app => {
        let chats = app.querySelectorAll('.person')
        chats.forEach((chat) => {
            chat.classList.remove('active-chat');
        })
    }

    const displayActiveChat = (id, app) => {
        // I only need to render new chat - old one doesn't have the style because of natural redndering
        ////console.log('Adding style to an active chat', app);
        let chats = app.querySelectorAll('.person')
        chats.forEach((chat) => {
            if (chat.id === id) {
                chat.classList.add('active-chat');
            }
        })
    }


    const router = async (toRender=[true, true]) => {
        //console.log("router is activated")
        let curPath = location.pathname;

        // Just '/' will not work because I have this route in flask.
        let routes = {
            '/home': {view: Home},
            '/contacts': {view: Contacts},
            '/profile': {view: EditProfile},
            '/settings': {view: Settings},
            '/chat': {view: Chat},
            '/edit': {view: EditProfile}
        }

        let globalId;

        if (chatRegex.test(curPath)) {
            //console.log('Chat page is calling...')
            let [page, id] = getViewChatId(curPath);
            globalId = id;
            // When reloading && chat is active to load the left
            // We must get the page every time chat is exist because chat is dynamic url and routes is static: we adjust dynamically the route to the page
            curPath = `/${page}`
            if (toRender[1]) {
                ////console.log("Router matching. Current page: " + page, "Id: " + id);
                // Loading right side when chat
                let chatMatch = routes['/chat']

                loadViewHTML(
                    new chatMatch.view(id), 
                    right
                )
            } 

            // Not render zero for changing pages on left
            if (!toRender[0] && window.innerWidth <= phoneViewportWidth) {
                // If the size of screen is phone like and we open chat, remove display of left
                // Some of the time to render new chat. Bad, but ok.
                setTimeout(() => {left.style.display = 'none'}, 100);
            }
        } else if (toRender[1]) {
            right.innerHTML = ""; // If chat is deleted, for example
        }
        
        if (toRender[0]) {
            // Loading left side all the time (when chat or when not)
            let match = routes[curPath];
            if (!match || match == undefined) {
                navigate('/home');
            } else {
                await loadViewHTML(
                    new match.view(),
                    left,
                    false // loadButtons. We don't wanna do this because only chat (above) can and wants
                )
            }
        } else {
            removeActiveChatStyle(left);
        }

        // Can't use it inside the chat because left is rendered after chat rendering
        if(globalId != undefined) {displayActiveChat(globalId, left);}
    }

    function navigate(url, toRender) {
        //console.log('Url to navigate is: ' + url)
        window.history.pushState(null, null, url);
        router(toRender);
    }

    window.addEventListener('popstate', router);

    window.addEventListener('DOMContentLoaded', async () => {
        //console.log('Page is reloaded. Starting router...')
        router();
    })


    const processView = (match, chat_id, app) => {
        let child = document.createElement('div');
        child.id = match.id;
        child.classList.add('container')
        match.setup(app, child);
        
        //console.log('Starting loading right sidebar html.')
        loadViewHTML(
            new match.view(chat_id),
            child,  // Assuming right is the id of the right side element in the DOM.
            false // Cycle loading otherwise.
        )
    }


    // I could adjust router to handle this, but I think that it's not the best option to do
    // So I would rather create a new one, even if it has some similar functionality
    // It's even better because it eleminates adaptation of router and its routes to buttonRouter and its routes, which differs
    const buttonRouter = (url, toSetStorage=true) => {
        const rightSidebar = document.getElementById('right-sidebar');

        // We append therefore there are problems with scripts.
        // Besides, styling preferencies and div checking requires to increase coupling.
        const routes = {
            '/chat-profile': {
                view: ChatProfile,
                id: 'chat-profile-container',
                setup: ((app, child) => {app.appendChild(child)})
            },
            '/edit-chat': {
                view: EditChat,
                id: 'edit-chat-container',
                setup: ((app, child) => {app.prepend(child)}) 
            },
            // I could integrate it to the chat-profile, but I think this is better 
            // because of less html on the page and more convenience, perhaps
            '/add-members': {
                view: AddMembers,
                id: 'add-members-container',
                setup: ((app, child) => {
                    // Temporarily adding members container to the chat profile container
                    // Don't remove app just for convenience
                    document.getElementById('chat-profile-container').prepend(child);
                })
            }
        }

        
        let match = routes[url];
        
        //console.log('Match in buttonRouter', url, match, rightSidebar)
        if (!match || !rightSidebar || rightSidebar.querySelector(`#${match.id}`) != undefined) {return;} 
        let chat_id = (location.pathname).match(chatRegex)[1];

        
        processView(match, chat_id, rightSidebar);

        if (toSetStorage && match.id !== 'add-members-container') {
            let cur = JSON.parse(localStorage.getItem('openedButtonViews')) || [];
            cur.push(url);
            localStorage.setItem('openedButtonViews', JSON.stringify(cur));
        }
        
    }

    document.querySelector('body').addEventListener('click', e => {
        //console.log('Click.', e.target, e, e.currentTarget);
        //alert('Click')
        ////console.log('Event clicked is:', e, e.target)
        /* TODO 
        I basically can create more event listeners to catch clicks with elements.
        However this fucntion will be activated every time.
        So it's unefficient, but convenient. 
        Let it be, but creating this event listener for all data-routing-link elements could be better (if possible).
        */

        if (e.target.matches('[data-routing-link]')) {
            //alert('Data routing link is clicked.')
            ////console.log('Data routing link is clicked. The link href is:', e.target.pathname, "The current pathname is:", location.pathname);
            
            // To move between pages seemlessly we let the right side to stay the same
            // So we can say a router not to render right side one time more
            let [lPage, lId] = getViewChatId(location.pathname, location.pathname);
            let [ePage, eId] = getViewChatId(e.target.pathname, e.target.pathname);
            //console.log(lPage, lId, ePage, eId, location.pathname, e.target.pathname);
            
            // If equaled, then stay the same, then don't need to render once again 
            let toRender = [
                !(ePage === lPage), // XOR function (^ doesn't work)
                (eId ? true : false)
            ]

            // Means changing current chat or clicking twice.
            // We remove all right chat sidebar.
            if (eId) {
                localStorage.setItem('openedButtonViews', JSON.stringify([]));
            }

            let chatRoute;
            if (lId !== null) {
                chatRoute = '/' + (eId === null ? lId : eId)
            } else {
                chatRoute = (eId === null ? "" : `/${eId}`)
            }

            // Page is always form the event, but the chat is if exists (settings, profile pages), then stays, if is switched then new one
            let nextRoute = `/${ePage}` + chatRoute
            //console.log(nextRoute, chatRoute, toRender)
            
            e.preventDefault();
            navigate(nextRoute, toRender);
        } else if (e.target.matches('[data-button-link]')) {
            // Only works to open the view and only one same page at a given time
            // Closing will be fully handled by scripts on click buttons
            // We have no routes, only buttons and interfaces
            //console.log('Data button link clicked.')
            e.preventDefault();
            buttonRouter(e.target.pathname);
        }

        //alert('finish')
    });

    const displayFromStorage = (path) => {
        let items = JSON.parse(localStorage.getItem(path)) || [];
        //console.log(items)
        for (let item of items) {
            if (item) {
                //console.log('Item: ' + item);
                buttonRouter(item, false);
            }
        }
    }

    Application.router = router;
    Application.navigate = navigate;
    Application.pageRegex = pageRegex;
    Application.getChatIdFromPathname = getChatIdFromPathname;
    Application.getPageNameFromPathname = getPageNameFromPathname;
}());

