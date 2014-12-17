
import py
import rstrategies as rs
from rpython.rlib.objectmodel import import_from_mixin

# === Define small model tree

class W_AbstractObject(object):
    pass

class W_Object(W_AbstractObject):
    pass

class W_Integer(W_AbstractObject):
    def __init__(self, value):
        self.value = value
    def __eq__(self, other):
        return isinstance(other, W_Integer) and self.value == other.value

class W_List(W_AbstractObject):
    rs.make_accessors()
    def __init__(self, strategy=None, size=0, elements=None):
        self.strategy = None
        if strategy:
            factory.set_initial_strategy(self, strategy, size, elements)
    def fetch(self, i):
        assert self.strategy
        return self.strategy.fetch(self, i)
    def store(self, i, value):
        assert self.strategy
        return self.strategy.store(self, i, value)
    def size(self):
        assert self.strategy
        return self.strategy.size(self)
    def insert(self, index0, list_w):
        assert self.strategy
        return self.strategy.insert(self, index0, list_w)
    def delete(self, start, end):
        assert self.strategy
        return self.strategy.delete(self, start, end)
    def append(self, list_w):
        assert self.strategy
        return self.strategy.append(self, list_w)
    def pop(self, index0):
        assert self.strategy
        return self.strategy.pop(self, index0)
    def slice(self, start, end):
        assert self.strategy
        return self.strategy.slice(self, start, end)
    def fetch_all(self):
        assert self.strategy
        return self.strategy.fetch_all(self)
    def store_all(self, elements):
        assert self.strategy
        return self.strategy.store_all(self, elements)

w_nil = W_Object()

# === Define concrete strategy classes

class AbstractStrategy(object):
    __metaclass__ = rs.StrategyMetaclass
    import_from_mixin(rs.AbstractStrategy)
    import_from_mixin(rs.SafeIndexingMixin)
    def __init__(self, w_self=None, size=0):
        pass
    def strategy_factory(self):
        return factory

class Factory(rs.StrategyFactory):
    switching_log = []
    
    def __init__(self, root_class):
        self.decorate_strategies({
            EmptyStrategy: [GenericStrategy],
            NilStrategy: [IntegerOrNilStrategy, GenericStrategy],
            GenericStrategy: [],
            WeakGenericStrategy: [],
                IntegerStrategy: [IntegerOrNilStrategy, GenericStrategy],
            IntegerOrNilStrategy: [GenericStrategy],
        })
        rs.StrategyFactory.__init__(self, root_class)
    
    def instantiate_strategy(self, strategy_type, w_self=None, size=0):
        return strategy_type(w_self, size)
    
    def set_strategy(self, w_list, strategy): 
        old_strategy = self.get_strategy(w_list)
        self.switching_log.append((old_strategy, strategy))
        super(Factory, self).set_strategy(w_list, strategy)
    
    def clear_log(self):
        del self.switching_log[:]

class EmptyStrategy(AbstractStrategy):
    import_from_mixin(rs.EmptyStrategy)

class NilStrategy(AbstractStrategy):
    import_from_mixin(rs.SingleValueStrategy)
    def value(self): return w_nil

class GenericStrategy(AbstractStrategy):
    import_from_mixin(rs.GenericStrategy)
    import_from_mixin(rs.UnsafeIndexingMixin)
    def default_value(self): return w_nil

class WeakGenericStrategy(AbstractStrategy):
    import_from_mixin(rs.WeakGenericStrategy)
    def default_value(self): return w_nil
    
class IntegerStrategy(AbstractStrategy):
    import_from_mixin(rs.SingleTypeStrategy)
    contained_type = W_Integer
    def wrap(self, value): return W_Integer(value)
    def unwrap(self, value): return value.value
    def default_value(self): return W_Integer(0)

class IntegerOrNilStrategy(AbstractStrategy):
    import_from_mixin(rs.TaggingStrategy)
    contained_type = W_Integer
    def wrap(self, value): return W_Integer(value)
    def unwrap(self, value): return value.value
    def default_value(self): return w_nil
    def wrapped_tagged_value(self): return w_nil
    def unwrapped_tagged_value(self): import sys; return sys.maxint
    
@rs.strategy(generalize=[], singleton=False)
class NonSingletonStrategy(GenericStrategy):
    def __init__(self, w_list=None, size=0):
        self.w_list = w_list
        self.size = size

class NonStrategy(NonSingletonStrategy):
    pass

factory = Factory(AbstractStrategy)

def check_contents(list, expected):
    assert list.size() == len(expected)
    for i, val in enumerate(expected):
        assert list.fetch(i) == val

def teardown():
    factory.clear_log()

# === Test Initialization and fetch

def test_setup():
    pass

def test_factory_setup():
    expected_strategies = 7
    assert len(factory.strategies) == expected_strategies
    assert len(set(factory.strategies)) == len(factory.strategies)
    for strategy in factory.strategies:
        assert isinstance(factory.strategy_instances[strategy], strategy)

def test_metaclass():
    assert NonStrategy._is_strategy == False
    assert IntegerOrNilStrategy._is_strategy == True
    assert IntegerOrNilStrategy._is_singleton == True
    assert NonSingletonStrategy._is_singleton == False
    assert NonStrategy._is_singleton == False
    assert NonStrategy.get_storage is not NonSingletonStrategy.get_storage

def test_singletons():
    def do_test_singletons(cls, expected_true):
        l1 = W_List(cls, 0)
        l2 = W_List(cls, 0)
        if expected_true:
            assert l1.strategy is l2.strategy
        else:
            assert l1.strategy is not l2.strategy
    do_test_singletons(EmptyStrategy, True)
    do_test_singletons(NonSingletonStrategy, False)
    do_test_singletons(NonStrategy, False)
    do_test_singletons(GenericStrategy, True)

def do_test_initialization(cls, default_value=w_nil, is_safe=True):
    size = 10
    l = W_List(cls, size)
    s = l.strategy
    assert s.size(l) == size
    assert s.fetch(l,0) == default_value
    assert s.fetch(l,size/2) == default_value
    assert s.fetch(l,size-1) == default_value
    py.test.raises(IndexError, s.fetch, l, size)
    py.test.raises(IndexError, s.fetch, l, size+1)
    py.test.raises(IndexError, s.fetch, l, size+5)
    if is_safe:
        py.test.raises(IndexError, s.fetch, l, -1)
    else:
        assert s.fetch(l, -1) == s.fetch(l, size - 1)

def test_init_Empty():
    l = W_List(EmptyStrategy, 0)
    s = l.strategy
    assert s.size(l) == 0
    py.test.raises(IndexError, s.fetch, l, 0)
    py.test.raises(IndexError, s.fetch, l, 10)
    
def test_init_Nil():
    do_test_initialization(NilStrategy)

def test_init_Generic():
    do_test_initialization(GenericStrategy, is_safe=False)
    
def test_init_WeakGeneric():
    do_test_initialization(WeakGenericStrategy)
    
def test_init_Integer():
    do_test_initialization(IntegerStrategy, default_value=W_Integer(0))
    
def test_init_IntegerOrNil():
    do_test_initialization(IntegerOrNilStrategy)
    
# === Test Simple store

def do_test_store(cls, stored_value=W_Object(), is_safe=True, is_varsize=False):
    size = 10
    l = W_List(cls, size)
    s = l.strategy
    def store_test(index):
        s.store(l, index, stored_value)
        assert s.fetch(l, index) == stored_value
    store_test(0)
    store_test(size/2)
    store_test(size-1)
    if not is_varsize:
        py.test.raises(IndexError, s.store, l, size, stored_value)
        py.test.raises(IndexError, s.store, l, size+1, stored_value)
        py.test.raises(IndexError, s.store, l, size+5, stored_value)
    if is_safe:
        py.test.raises(IndexError, s.store, l, -1, stored_value)
    else:
        store_test(-1)

def test_store_Nil():
    do_test_store(NilStrategy, stored_value=w_nil)

def test_store_Generic():
    do_test_store(GenericStrategy, is_safe=False)
    
def test_store_WeakGeneric():
    do_test_store(WeakGenericStrategy, stored_value=w_nil)
    
def test_store_Integer():
    do_test_store(IntegerStrategy, stored_value=W_Integer(100))
    
def test_store_IntegerOrNil():
    do_test_store(IntegerOrNilStrategy, stored_value=W_Integer(100))
    do_test_store(IntegerOrNilStrategy, stored_value=w_nil)

# === Test Insert

def do_test_insert(cls, values):
    l = W_List(cls, 0)
    s = l.strategy
    assert len(values) >= 6
    values1 = values[0:2]
    values2 = values[2:4]
    values3 = values[4:6]
    l.insert(0, values1+values3)
    check_contents(l, values1+values3)
    l.insert(2, values2)
    check_contents(l, values)

def test_insert_Nil():
    do_test_insert(NilStrategy, [w_nil]*6)

def test_insert_Generic():
    do_test_insert(GenericStrategy, [W_Object() for _ in range(6)])
    
def test_insert_WeakGeneric():
    do_test_insert(WeakGenericStrategy, [W_Object() for _ in range(6)])
    
def test_insert_Integer():
    do_test_insert(IntegerStrategy, [W_Integer(x) for x in range(6)])
    
def test_insert_IntegerOrNil():
    do_test_insert(IntegerOrNilStrategy, [w_nil]+[W_Integer(x) for x in range(4)]+[w_nil])
    do_test_insert(IntegerOrNilStrategy, [w_nil]*6)
    
# === Test Delete

# TODO

# === Test Transitions

def test_CheckCanHandle():
    def assert_handles(cls, good, bad):
        s = cls(0)
        for val in good:
            assert s.check_can_handle(val)
        for val in bad:
            assert not s.check_can_handle(val)
    obj = W_Object()
    i = W_Integer(0)
    nil = w_nil
    
    assert_handles(EmptyStrategy, [], [nil, obj, i])
    assert_handles(NilStrategy, [nil], [obj, i])
    assert_handles(GenericStrategy, [nil, obj, i], [])
    assert_handles(WeakGenericStrategy, [nil, obj, i], [])
    assert_handles(IntegerStrategy, [i], [nil, obj])
    assert_handles(IntegerOrNilStrategy, [nil, i], [obj])

def do_test_transition(OldStrategy, value, NewStrategy, initial_size=10):
    w = W_List(OldStrategy, initial_size)
    old = w.strategy
    w.store(0, value)
    assert isinstance(w.strategy, NewStrategy)
    assert factory.switching_log == [(None, old), (old, w.strategy)]

def test_AllNil_to_Generic():
    do_test_transition(NilStrategy, W_Object(), GenericStrategy)

def test_AllNil_to_IntegerOrNil():
    do_test_transition(NilStrategy, W_Integer(0), IntegerOrNilStrategy)

def test_IntegerOrNil_to_Generic():
    do_test_transition(IntegerOrNilStrategy, W_Object(), GenericStrategy)

def test_Integer_to_IntegerOrNil():
    do_test_transition(IntegerStrategy, w_nil, IntegerOrNilStrategy)

def test_Integer_Generic():
    do_test_transition(IntegerStrategy, W_Object(), GenericStrategy)

def test_TaggingValue_not_storable():
    tag = IntegerOrNilStrategy(10).unwrapped_tagged_value() # sys.maxint
    do_test_transition(IntegerOrNilStrategy, W_Integer(tag), GenericStrategy)

# TODO - Add VarsizeInteger, Übergang nach Empty etc
# - store maxint in IntegerOrNil

# TODO Test slice, fetch_all, append, pop, store_all

# === Test Weak Strategy
# TODO

# === Other tests

def test_optimized_strategy_switch(monkeypatch):
    l = W_List(NilStrategy, 5)
    s = l.strategy
    s.copied = 0
    def convert_storage_from_default(self, w_self, other):
        assert False, "The default convert_storage_from() should not be called!"
    def convert_storage_from_special(self, w_self, other):
        s.copied += 1
    
    monkeypatch.setattr(AbstractStrategy, "convert_storage_from_NilStrategy", convert_storage_from_special)
    monkeypatch.setattr(AbstractStrategy, "convert_storage_from", convert_storage_from_default)
    try:
        factory.switch_strategy(l, s, IntegerOrNilStrategy)
    finally:
        monkeypatch.undo()
    assert s.copied == 1, "Optimized switching routine not called exactly one time."
