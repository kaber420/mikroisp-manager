export interface Queue {
    id?: string;
    ".id"?: string;
    name: string;
    "max-limit"?: string;
    target?: string;
    comment?: string;
    disabled?: boolean | string;
}
