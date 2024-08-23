(function() {
    const textElement = document.getElementById('profile-copy-text');
    const copyButton = document.getElementById('profile-copy-button');
    
    copyButton.addEventListener('click', () => {
        Application.handleCopy(textElement.innerHTML);
        Application.popInfo('Email was copied. ');
    })
    
}());