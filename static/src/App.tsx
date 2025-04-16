import React, { useState } from 'react';
import { Stamp as Steam, X, ChevronDown, Download, ArrowUpDown, ShoppingCart, Check, Minus, Copy } from 'lucide-react';

type Currency = {
  label: string;
  symbol: string;
};

type FilterOption = {
  label: string;
  value: string;
};

type InventoryItem = {
  id: string;
  name: string;
  image: string;
  basePrice: number;
  marketPrice: number;
  quantity: number;
  inCart: boolean;
};

const currencies: Currency[] = [
  { label: 'Рубль', symbol: '₽' },
  { label: 'Доллар', symbol: '$' },
  { label: 'Евро', symbol: '€' },
  { label: 'Юань', symbol: '¥' },
  { label: 'Тенге', symbol: '₸' },
  { label: 'Бел. рубль', symbol: 'Br' },
];

const sourceOptions: FilterOption[] = [
  { label: 'Steam', value: 'steam' },
  { label: 'Buff163', value: 'buff163' },
  { label: 'TM Market', value: 'tm_market' },
];

const tradabilityOptions: FilterOption[] = [
  { label: 'Все', value: 'all' },
  { label: 'Трейд', value: 'trade' },
  { label: 'Продажа', value: 'sale' },
];

const categoryOptions: FilterOption[] = [
  { label: 'Все', value: 'all' },
  { label: 'Ножи', value: 'knives' },
  { label: 'Перчатки', value: 'gloves' },
  { label: 'Пистолеты', value: 'pistols' },
];

const viewModeOptions: FilterOption[] = [
  { label: 'Одиночный', value: 'single' },
  { label: 'Группировать', value: 'grouped' },
];

const sampleItems: InventoryItem[] = Array.from({ length: 12 }, (_, i) => ({
  id: `item-${i}`,
  name: i % 2 === 0 ? "Scavenging Guttleslug" : "Dragon Lore (Factory New)",
  image: `https://community.fastly.steamstatic.com/economy/image/-9a81dlWLwJ2UUGcVs_nsVtzdOEdtWwKGZZLQHTxDZ7I56KU0Zwwo4NUX4oFJZEHLbXH5ApeO4YmlhxYQknCRvCo04DEVlxkKgpot621FAR17P7NdTRH-t26q4SZlvD7PYTQgXtu5Mx2gv2PrdSijAWwqkVtN272JIGdJw46YVrYqVO3xLy-gJC9u5vByCBh6ygi7WGdwUKTYdRD8A/360fx360f`,
  basePrice: 150.20,
  marketPrice: 180.20,
  quantity: Math.floor(Math.random() * 20) + 1,
  inCart: false,
}));

function FilterDropdown({ options, value, onChange, label }: { 
  options: FilterOption[],
  value: string,
  onChange: (value: string) => void,
  label: string
}) {
  const [isOpen, setIsOpen] = useState(false);
  const selected = options.find(opt => opt.value === value);

  return (
    <div className="relative">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-[150px] h-10 bg-[#2C3035] rounded-lg px-3 text-white/90 flex items-center justify-between border-2 border-white/20 focus:outline-none hover:border-white/30 transition-colors"
      >
        <span className="text-sm">{selected?.label}</span>
        <ChevronDown size={18} className={`transition-transform ${isOpen ? 'rotate-180' : ''}`} />
      </button>

      {isOpen && (
        <div className="absolute top-12 left-0 w-[150px] bg-[#2C3035] rounded-xl border-2 border-white/20 shadow-lg z-50">
          {options.map((option) => (
            <button
              key={option.value}
              onClick={() => {
                onChange(option.value);
                setIsOpen(false);
              }}
              className={`w-full text-left px-3 py-2 text-sm hover:bg-[#3C73DD]/20 transition-colors ${
                value === option.value ? 'text-white' : 'text-white/50'
              }`}
            >
              {option.label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

function ItemCard({ item, currency, onToggleCart }: { 
  item: InventoryItem, 
  currency: Currency,
  onToggleCart: (id: string) => void
}) {
  const copyToClipboard = async (text: string) => {
    try {
      await navigator.clipboard.writeText(text);
    } catch (err) {
      console.error('Failed to copy text: ', err);
    }
  };

  const singlePrice = item.marketPrice;
  const totalPrice = singlePrice * item.quantity;

  const handleCartAction = (e: React.MouseEvent) => {
    e.stopPropagation();
    onToggleCart(item.id);
  };

  return (
    <div 
      className="w-full bg-[#2C3035] rounded-lg overflow-hidden group relative"
      style={{ boxShadow: '0 4px 6px rgba(0, 0, 0, 0.1)' }}
    >
      <div className="relative aspect-[270/178] bg-gradient-to-b from-[#3C3C3C] to-[#2C2C2C]">
        <img 
          src={item.image} 
          alt={item.name}
          className="w-full h-full object-cover"
        />
        <div 
          className="absolute inset-0 bg-black/60 backdrop-blur-sm opacity-0 group-hover:opacity-100 transition-opacity duration-200 flex flex-col items-center justify-center"
        >
          {item.inCart ? (
            <div className="flex flex-col items-center gap-3 w-[140px]">
              <button
                className="w-full h-10 bg-[#4EC75A] hover:bg-[#5FD86B] transition-colors rounded-lg font-bold text-sm text-white/90 shadow-md flex items-center justify-center gap-2"
                disabled
              >
                <ShoppingCart size={18} />
                В КОРЗИНЕ
              </button>
              <div className="w-full h-[1px] bg-white/20" />
              <button
                onClick={handleCartAction}
                className="w-full h-10 bg-[#FF4A4A] hover:bg-[#FF5C5C] transition-colors rounded-lg font-bold text-sm text-white/90 shadow-md"
              >
                УБРАТЬ
              </button>
            </div>
          ) : (
            <button
              onClick={handleCartAction}
              className="text-sm font-bold text-[#3677AB] uppercase underline hover:text-[#4488CC] transition-colors"
            >
              ДОБАВИТЬ
            </button>
          )}
        </div>
      </div>

      <div className="h-[1px] bg-[#707071]" />

      <div className="p-3">
        <div 
          onClick={() => copyToClipboard(item.name)}
          className="group/name relative flex items-start gap-1.5 mb-2 cursor-pointer"
        >
          <h3 className="text-sm font-medium text-white/95 text-left break-words">
            {item.name}
          </h3>
          <Copy size={14} className="text-white/50 opacity-0 group-hover/name:opacity-100 transition-opacity mt-0.5 shrink-0" />
        </div>
        
        <div className="grid grid-cols-2 gap-2 text-[10px] sm:text-xs">
          <div className="text-white/50">Количество</div>
          <div className="text-white/50 text-right">Стоимость</div>
          
          <div 
            className="text-white cursor-pointer hover:text-[#4DAEFC] transition-colors whitespace-nowrap"
            onClick={() => copyToClipboard('1')}
          >
            1 шт
          </div>
          <div 
            className="text-[#4DAEFC] cursor-pointer hover:text-[#6DBFFF] transition-colors text-right whitespace-nowrap"
            onClick={() => copyToClipboard(`${singlePrice.toFixed(2)} ${currency.symbol}`)}
          >
            {singlePrice.toFixed(2)}&nbsp;{currency.symbol}
          </div>
          
          <div 
            className="text-white cursor-pointer hover:text-[#06FF4C] transition-colors whitespace-nowrap"
            onClick={() => copyToClipboard(item.quantity.toString())}
          >
            {item.quantity} шт
          </div>
          <div 
            className="text-[#06FF4C] cursor-pointer hover:text-[#39FF73] transition-colors text-right whitespace-nowrap"
            onClick={() => copyToClipboard(`${totalPrice.toFixed(2)} ${currency.symbol}`)}
          >
            {totalPrice.toFixed(2)}&nbsp;{currency.symbol}
          </div>
        </div>
      </div>

      {item.inCart && (
        <div className="absolute top-2 right-2 w-6 h-6 bg-[#4EC75A] rounded-full flex items-center justify-center">
          <Check size={14} className="text-white" />
        </div>
      )}
    </div>
  );
}

function CartSidebar({ isOpen, onClose, items, currency, onRemoveItem }: {
  isOpen: boolean;
  onClose: () => void;
  items: InventoryItem[];
  currency: Currency;
  onRemoveItem: (id: string) => void;
}) {
  const cartItems = items.filter(item => item.inCart);
  const total = cartItems.reduce((sum, item) => sum + item.marketPrice, 0);

  return (
    <div 
      className={`fixed top-0 right-0 w-[320px] h-full bg-[#2C3035] shadow-xl transform transition-transform duration-300 ease-in-out z-[10000] ${
        isOpen ? 'translate-x-0' : 'translate-x-full'
      }`}
      style={{ boxShadow: '-4px 0 10px rgba(0, 0, 0, 0.2)' }}
    >
      <div className="p-4 h-full flex flex-col">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-bold text-white">Корзина</h2>
          <button 
            onClick={onClose}
            className="text-white/50 hover:text-white transition-colors p-1"
          >
            <X size={20} />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto">
          {cartItems.map(item => (
            <div 
              key={item.id} 
              className="flex items-center gap-3 p-3 bg-[#191C22] rounded-lg mb-3"
            >
              <img 
                src={item.image} 
                alt={item.name}
                className="w-16 h-16 object-cover rounded-md"
              />
              <div className="flex-1">
                <h3 className="text-sm font-medium text-white/90 mb-1 truncate">
                  {item.name}
                </h3>
                <p className="text-sm font-bold text-[#06FF4C]">
                  {currency.symbol} {item.marketPrice.toFixed(2)}
                </p>
              </div>
              <button
                onClick={() => onRemoveItem(item.id)}
                className="p-1.5 text-white/50 hover:text-white/80 transition-colors"
              >
                <Minus size={16} />
              </button>
            </div>
          ))}
        </div>

        <div className="border-t border-white/10 pt-3 mt-3">
          <div className="flex items-center justify-between mb-3">
            <span className="text-base text-white/70">Итого:</span>
            <span className="text-lg font-bold text-[#06FF4C]">
              {currency.symbol} {total.toFixed(2)}
            </span>
          </div>
          <button className="w-full h-10 bg-[#3C73DD] hover:bg-[#4d82ec] transition-colors rounded-lg font-bold text-sm text-white/90 shadow-md">
            ОФОРМИТЬ ЗАКАЗ
          </button>
        </div>
      </div>
    </div>
  );
}

function App() {
  const [profileUrl, setProfileUrl] = useState('');
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const [selectedCurrency, setSelectedCurrency] = useState(currencies[0]);
  const [showInventory, setShowInventory] = useState(false);
  const [isCartOpen, setIsCartOpen] = useState(false);
  
  const [source, setSource] = useState('steam');
  const [tradability, setTradability] = useState('all');
  const [category, setCategory] = useState('all');
  const [viewMode, setViewMode] = useState('single');
  
  const [items, setItems] = useState(sampleItems);

  const toggleItemInCart = (id: string) => {
    setItems(items.map(item => 
      item.id === id ? { ...item, inCart: !item.inCart } : item
    ));
  };

  const cartItemCount = items.filter(item => item.inCart).length;

  return (
    <main className="min-h-screen w-full bg-[#191C22] text-white">
      <header className="header-fixed h-20 px-6 flex items-center justify-between">
        <div className="flex items-center">
          <h1 className="text-lg font-bold tracking-wide text-white drop-shadow-sm">
            Steam Inventory
          </h1>
        </div>
        
        <button className="bg-[#3C73DD] hover:bg-[#4d82ec] transition-colors duration-200 px-4 py-2 rounded-xl font-bold text-sm shadow-md flex items-center gap-2">
          <Steam size={18} />
          ВОЙТИ ЧЕРЕЗ STEAM
        </button>
      </header>

      <div className="hero-banner w-full h-[600px] bg-[#212327] relative overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-b from-transparent to-black/20"></div>
        <img 
          src="https://steaminventory.ru/background.png" 
          alt="Gaming Heroes Banner"
          className="w-full h-full object-cover"
          style={{ objectPosition: 'center 25%' }}
        />
      </div>

      <div className="p-6 w-full">
        <div className="w-full min-h-[calc(100vh-4rem)] rounded-2xl bg-[#1E2128] p-8 shadow-lg">
          <div className="w-full text-center mt-6 mb-8">
            <p className="text-base leading-relaxed text-white/90 mb-3">
              SkinSpace Sorter – это сервис, позволяющий узнать стоимость инвентаря по каждой игре из вашего аккаунта в Steam.
            </p>
            <p className="text-base leading-relaxed text-white/90">
              Наш сайт позволяет оценить стоимость инвентаря таких игр как: CS:GO, DOTA 2, RUST и других.
            </p>
          </div>

          <div className="w-full">
            <label className="block text-sm text-white/70 mb-4 text-center">
              Вставьте в данное поле ссылку на ваш профиль в Steam, Steam ID или ссылку на Маркет и выберите валюту.
            </label>

            <div className="flex items-center justify-center gap-3 max-w-[1000px] mx-auto">
              <div className="relative flex-1">
                <input
                  type="text"
                  value={profileUrl}
                  onChange={(e) => setProfileUrl(e.target.value)}
                  placeholder="https://steamcommunity.com/profiles/76561198083135565/"
                  className="w-full h-10 bg-[#313131] border-2 border-[#414141] rounded-lg px-3 text-sm text-white/90 placeholder:text-white/50 focus:outline-none focus:border-[#3C73DD]"
                />
                {profileUrl && (
                  <button
                    onClick={() => setProfileUrl('')}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-white/50 hover:text-white/80 transition-colors"
                  >
                    <X size={16} />
                  </button>
                )}
              </div>

              <div className="relative">
                <button
                  onClick={() => setIsDropdownOpen(!isDropdownOpen)}
                  className="h-10 w-[150px] bg-[#2C3035] rounded-lg px-3 text-sm text-white/90 flex items-center justify-between border-2 border-[#414141] focus:outline-none focus:border-[#3C73DD]"
                >
                  <span>{`${selectedCurrency.label} (${selectedCurrency.symbol})`}</span>
                  <ChevronDown size={16} className={`transition-transform ${isDropdownOpen ? 'rotate-180' : ''}`} />
                </button>

                {isDropdownOpen && (
                  <div className="absolute top-12 right-0 w-[150px] bg-[#2C3035] rounded-xl border-2 border-white/20 shadow-lg z-50">
                    {currencies.map((currency) => (
                      <button
                        key={currency.symbol}
                        onClick={() => {
                          setSelectedCurrency(currency);
                          setIsDropdownOpen(false);
                        }}
                        className={`w-full text-left px-3 py-2 text-sm hover:bg-[#3C73DD]/20 transition-colors ${
                          selectedCurrency.symbol === currency.symbol ? 'text-white' : 'text-white/50'
                        }`}
                      >
                        {`${currency.label} (${currency.symbol})`}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            </div>

            <div className="flex justify-center mt-6">
              <button 
                className="w-[200px] h-[48px] bg-[#3C73DD] hover:bg-[#4d82ec] hover:scale-[1.02] transition-all duration-200 rounded-xl font-bold text-sm text-white/95 shadow-lg shadow-[#3C73DD]/20"
                onClick={() => setShowInventory(true)}
              >
                УЗНАТЬ СТОИМОСТЬ
              </button>
            </div>

            {showInventory && (
              <div className="w-full mt-8">
                <div className="w-full bg-[#2C3035] rounded-xl shadow-lg p-4 sm:p-6 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 sm:gap-6">
                  <div className="flex flex-col sm:flex-row items-start sm:items-center gap-4 sm:gap-6 w-full sm:w-auto">
                    <div className="w-[100px] h-[100px] rounded-lg overflow-hidden bg-[#1E2128] shrink-0">
                      <img 
                        src="https://avatars.fastly.steamstatic.com/fa31773ad3befce64be98fc74a8371ffa53069ec_full.jpg" 
                        alt="User Avatar"
                        className="w-full h-full object-cover"
                      />
                    </div>
                    <div>
                      <h2 className="text-xl font-bold text-white/95 mb-2">
                        Obivan Kenobi
                      </h2>
                      <div className="flex flex-col gap-1">
                        <span className="text-base font-medium text-white/50">
                          Стоимость инвентаря по CS:GO:
                        </span>
                        <span className="text-2xl font-semibold text-[#4DAEFC] whitespace-nowrap">
                          54645 {selectedCurrency.symbol}
                        </span>
                      </div>
                    </div>
                  </div>

                  <div className="flex flex-col items-start sm:items-end gap-3 w-full sm:w-auto">
                    <span className="text-base font-medium text-white/70">
                      Скачать стоимость инвентаря в txt формате:
                    </span>
                    <button className="w-full sm:w-[140px] h-[40px] bg-[#3C73DD] hover:bg-[#4d82ec] transition-colors duration-200 rounded-xl font-bold text-sm text-white/95 shadow-md flex items-center justify-center gap-2">
                      <Download size={16} />
                      СКАЧАТЬ
                    </button>
                  </div>
                </div>

                <div className="w-full mt-6">
                  <div className="flex items-center justify-between mb-4">
                    <span className="text-base text-white/90">
                      Всего в инвентаре по CS:GO найдено 1090 скинов (500 платные):
                    </span>
                  </div>

                  <div className="grid grid-cols-2 sm:flex items-center gap-4 mb-6 flex-wrap">
                    <FilterDropdown
                      options={sourceOptions}
                      value={source}
                      onChange={setSource}
                      label="Source"
                    />
                    <FilterDropdown
                      options={tradabilityOptions}
                      value={tradability}
                      onChange={setTradability}
                      label="Tradability"
                    />
                    <FilterDropdown
                      options={categoryOptions}
                      value={category}
                      onChange={setCategory}
                      label="Category"
                    />
                    <FilterDropdown
                      options={viewModeOptions}
                      value={viewMode}
                      onChange={setViewMode}
                      label="View Mode"
                    />

                    <div className="col-span-2 sm:ml-auto flex items-center gap-6">
                      <button className="uppercase text-sm font-medium text-white/50 flex items-center gap-1">
                        Кол-во
                        <ArrowUpDown size={14} />
                      </button>
                      <button className="uppercase text-sm font-medium text-white/50 flex items-center gap-1">
                        Цена
                        <ArrowUpDown size={14} />
                      </button>
                    </div>
                  </div>

                  <div className="w-full bg-[#1E2128] rounded-xl p-6">
                    <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 lg:grid-cols-6 xl:grid-cols-8 2xl:grid-cols-10 gap-4">
                      {items.map((item) => (
                        <ItemCard
                          key={item.id}
                          item={item}
                          currency={selectedCurrency}
                          onToggleCart={toggleItemInCart}
                        />
                      ))}
                    </div>

                    <div className="flex justify-center items-center gap-2 mt-6">
                      {[1, 2, 3, '...', 100].map((page, index) => (
                        <button
                          key={index}
                          className={`w-8 h-8 flex items-center justify-center rounded-lg ${
                            page === 1 
                              ? 'bg-[#3C73DD] text-white' 
                              : 'text-white/50 hover:text-white hover:bg-[#2C3035]'
                          }`}
                        >
                          {page}
                        </button>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      <button
        onClick={() => setIsCartOpen(true)}
        className="fixed bottom-6 right-6 w-12 h-12 bg-[#2C3035] rounded-full shadow-lg flex items-center justify-center hover:bg-[#3C3C3C] transition-colors z-[10000]"
        style={{ boxShadow: '0 4px 10px rgba(0, 0, 0, 0.2)' }}
      >
        <ShoppingCart size={20} className="text-white" />
        {cartItemCount > 0 && (
          <div className="absolute -top-1 -right-1 min-w-[20px] h-[20px] bg-[#3C73DD] rounded-full flex items-center justify-center px-1.5 text-xs font-bold text-white">
            {cartItemCount}
          </div>
        )}
      </button>

      <CartSidebar
        isOpen={isCartOpen}
        onClose={() => setIsCartOpen(false)}
        items={items}
        currency={selectedCurrency}
        onRemoveItem={toggleItemInCart}
      />
    </main>
  );
}

export default App;