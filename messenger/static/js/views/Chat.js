import AbstractView from "./AbstractView.js";

export default class extends AbstractView {
    constructor(id) {
        super();
        this.path = `/view/chat/${id}`;
    }

    // If not chat this id. I'll send literally nothing.
}