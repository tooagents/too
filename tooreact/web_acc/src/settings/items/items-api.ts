import { apiFetch } from 'src/core/apihttp';

// A catalog item as returned by /inv/settings/get_item_list (ItemOut).
export type Item = {
    id: string;
    item_number: string | null;
    item_name: string | null;
    item_rate: number | string | null;
    item_unit_of_measure: string | null;
    item_unit: string | null;
    item_sku: string | null;
    item_description: string | null;
    item_quantity: number | string | null;
    item_note: string | null;
    item_amount: number | string | null;
};

// Fields the form sends to post_item (ItemCreate). Passing `id` updates in place.
export type ItemUpsert = {
    id?: string | null;
    item_number?: string | null;
    item_name?: string | null;
    item_rate?: number | null;
    item_unit_of_measure?: string | null;
    item_unit?: string | null;
    item_sku?: string | null;
    item_description?: string | null;
    item_quantity?: number | null;
    item_note?: string | null;
    item_amount?: number | null;
};

async function parse<T>(response: Response, message: string): Promise<T> {
    if (!response.ok) {
        const details = await response.text().catch(() => '');
        throw new Error(`${message}: ${response.status} ${response.statusText}${details ? ` - ${details}` : ''}`);
    }
    return response.json();
}

export const itemsAPI = {
    async listItems(): Promise<Item[]> {
        const response = await apiFetch('/inv/settings/get_item_list');
        return parse<Item[]>(response, 'Failed to fetch items');
    },

    // Create-or-update. Passing an id updates that item in place.
    async saveItem(payload: ItemUpsert): Promise<Item> {
        const response = await apiFetch('/inv/settings/post_item', {
            method: 'POST',
            body: JSON.stringify(payload),
        });
        return parse<Item>(response, 'Failed to save item');
    },

    async deleteItem(itemId: string): Promise<void> {
        const response = await apiFetch(
            `/inv/settings/delete_item?item_id=${encodeURIComponent(itemId)}`,
            { method: 'DELETE' },
        );
        if (!response.ok) {
            const details = await response.text().catch(() => '');
            throw new Error(`Failed to delete item: ${response.status} ${response.statusText}${details ? ` - ${details}` : ''}`);
        }
    },
};

export default itemsAPI;
