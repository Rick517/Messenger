const eye = document.getElementById('eye');
const password_input = document.getElementById('password');
var sign = ['fa-eye', 'fa-eye-slash'];

const changeView = () => {
    password_input.type = sign[0] === 'fa-eye' ? 'text' : 'password';
}

eye.addEventListener('click', () => {
    //console.log('eye clicked.')
    eye.classList.remove(sign[0]);
    eye.classList.add(sign[1]);
    changeView();
    sign = sign.reverse();
})
