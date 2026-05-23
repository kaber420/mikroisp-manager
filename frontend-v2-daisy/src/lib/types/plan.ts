export interface Plan {
    id: number | string;
    name: string;
    max_limit: string;
    parent_queue?: string | null;
    comment?: string | null;
    router_host?: string | null;
    router_name?: string | null;
    price?: number;
    plan_type?: string | null;
    profile_name?: string | null;
    suspension_method?: string | null;
    address_list_strategy?: string | null;
    address_list_name?: string | null;
    v6_queue_type?: string | null;
    v7_queue_type?: string | null;
}

export interface PlanCreate {
    name: string;
    max_limit: string;
    parent_queue?: string | null;
    comment?: string | null;
    router_host?: string | null;
    price?: number;
    plan_type?: string | null;
    profile_name?: string | null;
    suspension_method?: string | null;
    address_list_strategy?: string | null;
    address_list_name?: string | null;
    v6_queue_type?: string | null;
    v7_queue_type?: string | null;
}

export interface PlanUpdate {
    name?: string | null;
    max_limit?: string | null;
    parent_queue?: string | null;
    comment?: string | null;
    router_host?: string | null;
    price?: number | null;
    plan_type?: string | null;
    profile_name?: string | null;
    suspension_method?: string | null;
    address_list_strategy?: string | null;
    address_list_name?: string | null;
    v6_queue_type?: string | null;
    v7_queue_type?: string | null;
}
