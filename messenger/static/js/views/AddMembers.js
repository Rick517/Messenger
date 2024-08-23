import AbstractView from "./AbstractView.js";

export default class extends AbstractView {
    constructor(chat_id) {
        super();
        this.path = '/view/add-members/' + chat_id;
    }
}