(function() {
    const button = document.getElementById('close-edit-chat');
    const container = document.getElementById('edit-chat-container');

    button.addEventListener('click', () => {
        container.remove();
        let data = JSON.parse(localStorage.getItem('openedButtonViews'));
        if (data) {
            localStorage.setItem('openedButtonViews', JSON.stringify(
                data.filter(item => item !== "/edit-chat")));
        }
    })
}());