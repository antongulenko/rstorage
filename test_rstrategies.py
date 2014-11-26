
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
    def __init__(self, strategy=None):
        self.strategy = strategy
        if strategy:
            strategy.w_list = self
    def fetch(self, i):
        assert self.strategy
        return self.strategy.fetch(i)
    def store(self, i, value):
        assert self.strategy
        return self.strategy.store(i, value)
    def size(self):
        assert self.strategy
        return self.strategy.size()

w_nil = W_Object()

# === Define concrete strategy classes

class AbstractStrategy(object):
    __metaclass__ = rs.StrategyMetaclass
    import_from_mixin(rs.AbstractCollection)
    def __init__(self, size):
        self.init_strategy(size)
        self.w_list = None
    def strategy_factory(self):
        return factory

class Factory(rs.StrategyFactory):
    switching_log = []
    
    def __init__(self, root_class):
        self.decorate_strategies({
            EmptyStrategy: [VarsizeGenericStrategy],
            NilStrategy: [IntegerOrNilStrategy, GenericStrategy],
            GenericStrategy: [],
            WeakGenericStrategy: [],
            VarsizeGenericStrategy: [],
            IntegerStrategy: [IntegerOrNilStrategy, GenericStrategy],
            IntegerOrNilStrategy: [GenericStrategy],
        })
        rs.StrategyFactory.__init__(self, root_class)
    
    def instantiate_empty(self, strategy_type):
        return strategy_type(0)
    
    def instantiate_and_switch(self, old_strategy, size, new_cls):
        inst = new_cls(size)
        self.switching_log.append((old_strategy, inst))
        if old_strategy.w_list:
            old_strategy.w_list.strategy = inst
        return inst
    
    def clear_log(self):
        del self.switching_log[:]

class EmptyStrategy(AbstractStrategy):
    import_from_mixin(rs.EmptyStrategy)
    def __init__(self, size=0):
        AbstractStrategy.__init__(self, size)

class NilStrategy(AbstractStrategy):
    import_from_mixin(rs.SingleValueStrategy)
    import_from_mixin(rs.SafeIndexingMixin)
    def value(self): return w_nil

class GenericStrategy(AbstractStrategy):
    import_from_mixin(rs.GenericStrategy)
    import_from_mixin(rs.UnsafeIndexingMixin)
    def default_value(self): return w_nil

class WeakGenericStrategy(AbstractStrategy):
    import_from_mixin(rs.WeakGenericStrategy)
    import_from_mixin(rs.SafeIndexingMixin)
    def default_value(self): return w_nil
    
class VarsizeGenericStrategy(AbstractStrategy):
    import_from_mixin(rs.GenericStrategy)
    import_from_mixin(rs.SafeIndexingMixin)
    def default_value(self): return w_nil

class IntegerStrategy(AbstractStrategy):
    import_from_mixin(rs.SingleTypeStrategy)
    import_from_mixin(rs.SafeIndexingMixin)
    contained_type = W_Integer
    def wrap(self, value): return W_Integer(value)
    def unwrap(self, value): return value.value
    def default_value(self): return W_Integer(0)

class IntegerOrNilStrategy(AbstractStrategy):
    import_from_mixin(rs.TaggingStrategy)
    import_from_mixin(rs.SafeIndexingMixin)
    contained_type = W_Integer
    def wrap(self, value): return W_Integer(value)
    def unwrap(self, value): return value.value
    def default_value(self): return w_nil
    def wrapped_tagged_value(self): return w_nil
    def unwrapped_tagged_value(self): import sys; return sys.maxint
    
class NonStrategy(IntegerOrNilStrategy):
    pass
    
factory = Factory(AbstractStrategy)

def check_contents(strategy, expected):
    assert strategy.size() == len(expected)
    for i, val in enumerate(expected):
        assert strategy.fetch(i) == val

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
        assert isinstance(strategy._strategy_instance, strategy)

def do_test_initialization(cls, default_value=w_nil, is_safe=True):
    size = 10
    s = cls(size)
    assert s.size() == size
    assert s.fetch(0) == default_value
    assert s.fetch(size/2) == default_value
    assert s.fetch(size-1) == default_value
    py.test.raises(IndexError, s.fetch, size)
    py.test.raises(IndexError, s.fetch, size+1)
    py.test.raises(IndexError, s.fetch, size+5)
    if is_safe:
        py.test.raises(IndexError, s.fetch, -1)
    else:
        assert s.fetch(-1) == s.fetch(size - 1)

def test_init_Empty():
    s = EmptyStrategy()
    assert s.size() == 0
    py.test.raises(IndexError, s.fetch, 0)
    py.test.raises(IndexError, s.fetch, 10)
    
def test_init_Nil():
    do_test_initialization(NilStrategy)

def test_init_Generic():
    do_test_initialization(GenericStrategy, is_safe=False)
    
def test_init_WeakGeneric():
    do_test_initialization(WeakGenericStrategy)
    
def test_init_VarsizeGeneric():
    do_test_initialization(VarsizeGenericStrategy)
    
def test_init_Integer():
    do_test_initialization(IntegerStrategy, default_value=W_Integer(0))
    
def test_init_IntegerOrNil():
    do_test_initialization(IntegerOrNilStrategy)
    
# === Test Simple store

def do_test_store(cls, stored_value=W_Object(), is_safe=True, is_varsize=False):
    size = 10
    s = cls(size)
    def store_test(index):
        s.store(index, stored_value)
        assert s.fetch(index) == stored_value
    store_test(0)
    store_test(size/2)
    store_test(size-1)
    if not is_varsize:
        py.test.raises(IndexError, s.store, size, stored_value)
        py.test.raises(IndexError, s.store, size+1, stored_value)
        py.test.raises(IndexError, s.store, size+5, stored_value)
    if is_safe:
        py.test.raises(IndexError, s.store, -1, stored_value)
    else:
        store_test(-1)

def test_store_Nil():
    do_test_store(NilStrategy, stored_value=w_nil)

def test_store_Generic():
    do_test_store(GenericStrategy, is_safe=False)
    
def test_store_WeakGeneric():
    do_test_store(WeakGenericStrategy, stored_value=w_nil)
    
def test_store_VarsizeGeneric():
    do_test_store(VarsizeGenericStrategy, is_varsize=True)
    
def test_store_Integer():
    do_test_store(IntegerStrategy, stored_value=W_Integer(100))
    
def test_store_IntegerOrNil():
    do_test_store(IntegerOrNilStrategy, stored_value=W_Integer(100))
    do_test_store(IntegerOrNilStrategy, stored_value=w_nil)

# === Test Delete

# TODO

# === Test Insert

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
    assert_handles(VarsizeGenericStrategy, [nil, obj, i], [])
    assert_handles(IntegerStrategy, [i], [nil, obj])
    assert_handles(IntegerOrNilStrategy, [nil, i], [obj])

def do_test_transition(OldStrategy, value, NewStrategy):
    w = W_List(OldStrategy(10))
    old = w.strategy
    w.store(0, value)
    assert isinstance(w.strategy, NewStrategy)
    assert factory.switching_log == [(old, w.strategy)]

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

def test_Empty_to_VarsizeGeneric():
    do_test_transition(EmptyStrategy, W_Integer(0), VarsizeGenericStrategy)
    factory.clear_log()
    do_test_transition(EmptyStrategy, W_Object(), VarsizeGenericStrategy)
    factory.clear_log()
    do_test_transition(EmptyStrategy, w_nil, VarsizeGenericStrategy)

def test_TaggingValue_not_storable():
    tag = IntegerOrNilStrategy(10).unwrapped_tagged_value() # sys.maxint
    do_test_transition(IntegerOrNilStrategy, W_Integer(tag), GenericStrategy)

# TODO - Add VarsizeInteger, Übergang nach Empty etc
# - store maxint in IntegerOrNil

# TODO Test slice, fetch_all, append, pop

# === Test Weak Strategy
# TODO

# === Other tests

def test_metaclass():
    assert VarsizeGenericStrategy._is_strategy == True
    assert NonStrategy._is_strategy == False
    assert IntegerOrNilStrategy._is_strategy == True

def test_optimized_strategy_switch(monkeypatch):
    s = NilStrategy(5)
    l = W_List(s)
    s.copied = 0
    def copy_from_default(self, other):
        assert False, "The default copy_from() routine should not be called!"
    def copy_from_special(self, other):
        s.copied += 1
    
    monkeypatch.setattr(AbstractStrategy, "copy_from_NilStrategy", copy_from_special)
    try:
        factory.switch_strategy(s, IntegerOrNilStrategy)
    finally:
        monkeypatch.undo()
    assert s.copied == 1, "Optimized switching routine not called exactly one time."
    