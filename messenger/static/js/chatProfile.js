(function() {
    const button = document.getElementById('close-chat-profile');
    const container = document.getElementById('chat-profile-container');
    const textElement = document.getElementById('chat-profile-copy-text');
    const copyButton = document.getElementById('chat-profile-copy-button');

    button.addEventListener('click', () => {
        container.remove();
        let data = JSON.parse(localStorage.getItem('openedButtonViews'));
        if (data) {
            localStorage.setItem('openedButtonViews', JSON.stringify(
                data.filter(item => item !== "/chat-profile")));
        }
    })

    if (copyButton != undefined) {
        copyButton.addEventListener('click', () => {
            Application.handleCopy(textElement.innerHTML);
            Application.popInfo('Email was copied. ');
        })
    }


}());