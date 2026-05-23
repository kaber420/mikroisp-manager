export interface Queue {
    id?: string;
    ".id"?: string;
    name: string;
    "max-limit"?: string;
    target?: string;
    comment?: string;
    disabled?: boolean | string;
}

export interface SimpleQueue {
    id?: string;
    ".id"?: string;
    name: string;
    target?: string;
    "max-limit"?: string;
    parent?: string;
    comment?: string;
    disabled?: boolean | string;
}
