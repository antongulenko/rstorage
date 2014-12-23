# rstrategies

A library to implement storage strategies in VMs based on the RPython toolchain.
rstrategies can be used in VMs for any language or language family.

This library has been developed as part of a Masters Thesis by [Anton Gulenko](https://github.com/antongulenko).

The original paper describing the optimization "Storage Strategies for collections in dynamically typed languages" by C.F. Bolz, L. Diekmann and L. Tratt can be found [here](http://stups.hhu.de/mediawiki/images/3/3b/Pub-BoDiTr13_246.pdf).

So far, this library has been adpoted by 3 VMs: [RSqueak](https://github.com/HPI-SWA-Lab/RSqueak), [Topaz](https://github.com/topazproject/topaz) ([Forked here](https://github.com/antongulenko/topaz/tree/rstrategies)) and [Pycket](https://github.com/samth/pycket) ([Forked here](https://github.com/antongulenko/pycket/tree/rstrategies)).

### Concept

Collections are often used homogeneously, i.e. they contain only objects of the same type.
Primitive numeric types like ints or floats are especially interesting for optimization.
These cases can be optimized by storing the unboxed data of these objects in consecutive memory.
This is done by letting a special "strategy" object handle the entire storage of a collection.
The collection object holds separate references to its strategy and its storage, like shown here below.
Every operation on the collection is delegated to the strategy.
When needed, the strategy can be switched to a more suitable one, which might require converting the storage array.

collection --> strategy (singleton object)<br/>
          \--> storage (list of values)

## Usage

### Basics

The VM should have a class or class hierarchy for collections in a broader sense, for example types like arrays, lists or regular objects.
This library supports fixed sized and variable sized collections.
In order to extend these classes and use strategies, the library need access to two attributes of collection objects: strategy and storage.
The easies way is adding the following line to the body of the root collection class:
```
rstrategies.make_accessors(strategy='strategy', storage='storage')
```
This will generate accessor methods ```_[get/set]_[storage/strategy]()``` for the attributes named in the call.
Alternatively, implement these methods manually.

Next, the strategy classes must be defined. This requires a small class hierarchy with a dedicated superclass.
In the definition of this superclass, include the following lines:

```
    __metaclass__ = rstrategies.StrategyMetaclass
    import_from_mixin(rstrategies.AbstractStrategy)
    import_from_mixin(rstrategies.SafeIndexingMixin)
```

```import_from_mixin``` can be found in ```rpython.rlib.objectmodel```.
If index-checking is performed safely at other places in the VM, you can use ```rstrategies.UnsafeIndexingMixin``` instead.
If you need your own metaclass, you can combine yours with the rstrategies one using multiple inheritance (like here)[https://github.com/HPI-SWA-Lab/RSqueak/blob/master/spyvm/storage_contexts.py#L23].
Also implement a ```storage_factory()``` method, which returns an instance of ```rstrategies.StorageFactory```, which is described below.

### Strategy classes

Now you can create the actual strategy classes, subclassing them from the single superclass.
The following list summarizes the basic strategies available.
* ```EmptyStrategy```
    A strategy for empty collections; very efficient, but limited. Does not allocate anything.
* ```SingleValueStrategy```
    A strategy for collections containing the same object ```n``` times. Only allocates memory to store the size of the collection.
* ```GenericStrategy```
    A non-optimized strategy backed by a generic python list. This is the fallback strategy, since it can store everything, but is not optimized.
* ```WeakGenericStrategy```
    Like ```GenericStrategy```, but uses ```weakref``` to hold on weakly to its elements.
* ```SingleTypeStrategy```
    Can store a single unboxed type like int or float
* ```TaggingStrategy```
    Extension of SingleTypeStrategy. Uses a specific value in the value range of the unboxed type to represent
    one additional, arbitrary object.

There are also intermediate classes, which allow creating new, more customized strategies. For this, you should get familiar with the code.

Include one of these mixin classes using ```import_from_mixin```.
The mixin classes contain comments describing methods or fields which are also required in the strategy class in order to use them.
Additionally, add the @rstrategies.strategy(generalize=alist) decorator to all strategy classes.
The list parameter must contain all strategies, which the decorated strategy can switch to, if it can not represent a new element anymore.
(Example)[https://github.com/HPI-SWA-Lab/RSqueak/blob/master/spyvm/storage.py#L64] for an implemented strategy.
See the other strategy classes behind this link for more examples.

### Strategy Factory

The last part is subclassing ```rstrategies.StrategyFactory```, overwriting the method ```instantiate_strategy``` if necessary, passing the strategies root class to the constructor.
The factory has the methods ```switch_strategy```, ```set_initial_strategy```, ```strategy_type_for``` which can be used by the VM code to use the mechanism behind strategies.
See the comments in the source code.

The strategy mixins offer the following methods to manipulate the contents of the collection:
* basic API
    * size
* fixed size API
    * store, fetch, slice, store_all, fetch_all
* variable size API
    * insert, delete, append, pop
If the collection has a fixed size, simply never use any of the variable size methods in the VM code.
Since the strategies are singletons, these methods need the collection object as first parameter.
For convenience, more fitting accessor methods should be implemented on the collection class itself.
