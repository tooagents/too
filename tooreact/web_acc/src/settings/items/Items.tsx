import { useEffect, useMemo, useState } from 'react';

import { TbDotsVertical } from 'react-icons/tb';
import { Icon } from '@iconify/react';

import LoadingSpinner from 'src/components/shared/LoadingSpinner';
import { Button } from 'src/components/ui/button';
import { Table, TBody, TCell, THead, THeader, TRow } from 'src/components/ui/table';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from 'src/components/ui/dropdown-menu';
import { Input } from 'src/components/ui/input';
import BreadcrumbComp from 'src/_layouts/shared/breadcrumb/BreadcrumbComp';
import { notifyToast } from 'src/core/toast';

import { itemsAPI, type Item } from './items-api';
import ItemFormModal from './ItemFormModal';

const BCrumb = [
    { to: '/', title: 'Home' },
    { title: 'Items' },
];

const pageSize = 20;

const fmtRate = (v: number | string | null): string => {
    if (v == null || v === '') return '-';
    const n = Number(v);
    return Number.isFinite(n) ? n.toFixed(2) : String(v);
};

const Items = () => {
    const [items, setItems] = useState<Item[]>([]);
    const [isLoading, setIsLoading] = useState(false);
    const [query, setQuery] = useState('');
    const [pageIndex, setPageIndex] = useState(0);
    const [isModalOpen, setIsModalOpen] = useState(false);
    const [editingItem, setEditingItem] = useState<Item | null>(null);

    const refreshItems = async () => {
        setIsLoading(true);
        try {
            setItems(await itemsAPI.listItems());
        } catch (err) {
            console.error('Failed to load items:', err);
            notifyToast({ message: 'Failed to load items.', variant: 'error' });
        } finally {
            setIsLoading(false);
        }
    };

    useEffect(() => {
        void refreshItems();
    }, []);

    const handleCreate = () => {
        setEditingItem(null);
        setIsModalOpen(true);
    };

    const handleEdit = (item: Item) => {
        setEditingItem(item);
        setIsModalOpen(true);
    };

    const handleDelete = async (itemId: string) => {
        try {
            await itemsAPI.deleteItem(itemId);
            await refreshItems();
        } catch (err) {
            console.error('Failed to delete item:', err);
            notifyToast({ message: 'Failed to delete item.', variant: 'error' });
        }
    };

    const filtered = useMemo(() => {
        if (!query.trim()) return items;
        const needle = query.trim().toLowerCase();
        return items.filter((row) =>
            Object.values(row).some((val) => String(val).toLowerCase().includes(needle)),
        );
    }, [items, query]);

    useEffect(() => {
        setPageIndex(0);
    }, [query, items.length]);

    const pageCount = Math.max(1, Math.ceil(filtered.length / pageSize));
    const pageData = useMemo(
        () => filtered.slice(pageIndex * pageSize, pageIndex * pageSize + pageSize),
        [filtered, pageIndex],
    );

    const canPrev = pageIndex > 0;
    const canNext = pageIndex + 1 < pageCount;

    return (
        <>
            <BreadcrumbComp title="Items" items={BCrumb} />

            <div className="flex gap-6 flex-col">
                <div className="flex flex-col sm:flex-row gap-2 items-stretch sm:items-center">
                    <div className="relative flex-1 min-w-0">
                        <Icon icon="solar:magnifer-linear" width="18" height="18" className="absolute left-3 top-1/2 -translate-y-1/2" />
                        <Input
                            type="text"
                            className="pl-9 rounded-md border-0 bg-gray-100/80 shadow-none placeholder:text-gray-400 focus-visible:ring-1 focus-visible:ring-secondary/40 focus-visible:ring-offset-0 dark:bg-slate-900/50 dark:placeholder:text-white/20"
                            value={query}
                            onChange={(e) => setQuery(e.target.value)}
                            placeholder="Search..."
                        />
                    </div>
                    <div className="flex flex-wrap items-center gap-2 sm:shrink-0">
                        <Button onClick={handleCreate} color="primary" className="flex items-center gap-1.5 rounded-md">
                            <Icon icon="solar:add-circle-outline" width="18" height="18" /> Add Item
                        </Button>
                    </div>
                </div>

                <div className="border rounded-md border-ld">
                    <Table>
                        <THeader>
                            <TRow>
                                <THead className="text-sm font-semibold pl-6">Name</THead>
                                <THead className="text-sm font-semibold">Item #</THead>
                                <THead className="text-sm font-semibold">SKU</THead>
                                <THead className="text-sm font-semibold">Unit</THead>
                                <THead className="text-sm font-semibold text-right">Rate</THead>
                                <THead className="text-sm font-semibold">Actions</THead>
                            </TRow>
                        </THeader>

                        <TBody>
                            {isLoading ? (
                                <TRow><TCell colSpan={6} className="text-center py-8">
                                    <div className="inline-flex items-center gap-2 text-gray-500">
                                        <LoadingSpinner size="md" />
                                    </div>
                                </TCell></TRow>
                            ) : filtered.length === 0 ? (
                                <TRow><TCell colSpan={6} className="text-center py-8">
                                    No items found
                                </TCell></TRow>
                            ) : (
                                pageData.map((item, index) => (
                                    <TRow key={item.id || `item-${index}`}>
                                        <TCell className="font-semibold pl-6">{item.item_name || '-'}</TCell>
                                        <TCell className="text-muted-foreground text-sm">{item.item_number || '-'}</TCell>
                                        <TCell className="text-muted-foreground text-sm">{item.item_sku || '-'}</TCell>
                                        <TCell className="text-muted-foreground text-sm">{item.item_unit_of_measure ?? item.item_unit ?? '-'}</TCell>
                                        <TCell className="text-right text-sm">{fmtRate(item.item_rate)}</TCell>
                                        <TCell>
                                            <DropdownMenu>
                                                <DropdownMenuTrigger asChild>
                                                    <span className="h-9 w-9 flex justify-center items-center rounded-full hover:bg-lightprimary hover:text-primary cursor-pointer">
                                                        <TbDotsVertical size={22} />
                                                    </span>
                                                </DropdownMenuTrigger>
                                                <DropdownMenuContent align="end" className="w-40">
                                                    <DropdownMenuItem className="flex gap-3 items-center cursor-pointer" onClick={() => handleEdit(item)}>
                                                        <Icon icon={'solar:pen-new-square-broken'} height={18} /><span>Edit</span>
                                                    </DropdownMenuItem>
                                                    <DropdownMenuItem className="flex gap-3 items-center cursor-pointer" onClick={() => item.id && void handleDelete(item.id)}>
                                                        <Icon icon={'solar:trash-bin-minimalistic-outline'} height={18} /><span>Delete</span>
                                                    </DropdownMenuItem>
                                                </DropdownMenuContent>
                                            </DropdownMenu>
                                        </TCell>
                                    </TRow>
                                ))
                            )}
                        </TBody>
                    </Table>
                </div>

                <div className="flex flex-col gap-4 p-2">
                    <div className="flex flex-col sm:flex-row items-center justify-between gap-3">
                        <div className="flex gap-2 w-full sm:w-auto">
                            <Button
                                onClick={() => setPageIndex((p) => Math.max(0, p - 1))}
                                disabled={!canPrev}
                                variant="secondary"
                                className="flex-1 sm:flex-none text-xs sm:text-sm"
                            >
                                Previous
                            </Button>
                            <Button
                                onClick={() => setPageIndex((p) => Math.min(pageCount - 1, p + 1))}
                                disabled={!canNext}
                                className="flex-1 sm:flex-none text-xs sm:text-sm"
                            >
                                Next
                            </Button>
                        </div>

                        <div className="text-forest-black dark:text-white/90 font-medium text-xs sm:text-base whitespace-nowrap">
                            Page {pageIndex + 1} of {pageCount}
                        </div>
                    </div>
                </div>

                <ItemFormModal
                    isOpen={isModalOpen}
                    onClose={() => setIsModalOpen(false)}
                    onComplete={async () => { setIsModalOpen(false); await refreshItems(); }}
                    initialData={editingItem}
                />
            </div>
        </>
    );
};

export default Items;
