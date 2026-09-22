import { useEffect, useState } from 'react';
import { Button } from 'src/components/ui/button';
import { Input } from 'src/components/ui/input';
import { Label } from 'src/components/ui/label';
import {
    Dialog,
    DialogContent,
    DialogFooter,
    DialogHeader,
    DialogTitle,
} from 'src/components/ui/dialog';
import { notifyToast } from 'src/core/toast';
import LoadingSpinner from 'src/components/shared/LoadingSpinner';

import { itemsAPI, type Item } from './items-api';

interface Props {
    isOpen: boolean;
    onClose: () => void;
    onComplete: () => void;
    initialData?: Item | null;
}

const numOrNull = (v: string): number | null => {
    const t = v.trim();
    if (!t) return null;
    const n = Number(t);
    return Number.isFinite(n) ? n : null;
};

const ItemFormModal = ({ isOpen, onClose, onComplete, initialData }: Props) => {
    const [id, setId] = useState<string | null>(null);
    const [itemName, setItemName] = useState('');
    const [itemNumber, setItemNumber] = useState('');
    const [itemSku, setItemSku] = useState('');
    const [itemRate, setItemRate] = useState('');
    const [itemUnit, setItemUnit] = useState('');
    const [itemDescription, setItemDescription] = useState('');

    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        if (isOpen) {
            setError(null);
            setId(initialData?.id ?? null);
            setItemName(initialData?.item_name ?? '');
            setItemNumber(initialData?.item_number ?? '');
            setItemSku(initialData?.item_sku ?? '');
            setItemRate(initialData?.item_rate != null ? String(initialData.item_rate) : '');
            setItemUnit(initialData?.item_unit_of_measure ?? initialData?.item_unit ?? '');
            setItemDescription(initialData?.item_description ?? '');
        }
    }, [isOpen, initialData]);

    const handleSave = async () => {
        if (!itemName.trim()) {
            setError('An item name is required.');
            return;
        }
        setLoading(true);
        setError(null);
        try {
            await itemsAPI.saveItem({
                ...(id ? { id } : {}),
                item_name: itemName.trim(),
                item_number: itemNumber.trim() || null,
                item_sku: itemSku.trim() || null,
                item_rate: numOrNull(itemRate),
                item_unit_of_measure: itemUnit.trim() || null,
                item_description: itemDescription.trim() || null,
            });
            notifyToast({ message: id ? 'Item updated.' : 'Item created.', variant: 'success' });
            onComplete();
        } catch (err) {
            const message = err instanceof Error ? err.message : 'Failed to save item';
            setError(message);
        } finally {
            setLoading(false);
        }
    };

    return (
        <Dialog open={isOpen} onOpenChange={(open) => { if (!open) onClose(); }}>
            <DialogContent className="sm:max-w-lg">
                <DialogHeader>
                    <DialogTitle>{id ? 'Edit item' : 'New item'}</DialogTitle>
                </DialogHeader>

                <div className="grid grid-cols-2 gap-3">
                    <div className="col-span-2 flex flex-col gap-1.5">
                        <Label>Name</Label>
                        <Input value={itemName} onChange={(e) => setItemName(e.target.value)} placeholder="Item name" disabled={loading} />
                    </div>
                    <div className="flex flex-col gap-1.5">
                        <Label>Item #</Label>
                        <Input value={itemNumber} onChange={(e) => setItemNumber(e.target.value)} placeholder="ITEM-001" disabled={loading} />
                    </div>
                    <div className="flex flex-col gap-1.5">
                        <Label>SKU</Label>
                        <Input value={itemSku} onChange={(e) => setItemSku(e.target.value)} disabled={loading} />
                    </div>
                    <div className="flex flex-col gap-1.5">
                        <Label>Rate</Label>
                        <Input type="number" inputMode="decimal" value={itemRate} onChange={(e) => setItemRate(e.target.value)} placeholder="0.00" disabled={loading} />
                    </div>
                    <div className="flex flex-col gap-1.5">
                        <Label>Unit</Label>
                        <Input value={itemUnit} onChange={(e) => setItemUnit(e.target.value)} placeholder="each / hr" disabled={loading} />
                    </div>
                    <div className="col-span-2 flex flex-col gap-1.5">
                        <Label>Description</Label>
                        <Input value={itemDescription} onChange={(e) => setItemDescription(e.target.value)} disabled={loading} />
                    </div>
                </div>

                {error && <p className="text-sm text-red-500">{error}</p>}

                <DialogFooter>
                    <Button variant="secondary" onClick={onClose} disabled={loading}>Cancel</Button>
                    <Button color="primary" onClick={() => void handleSave()} disabled={loading}>
                        {loading ? <LoadingSpinner size="sm" /> : id ? 'Save' : 'Create'}
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
};

export default ItemFormModal;
