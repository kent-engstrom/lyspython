# Heap class

# Written by Peter Liljenberg <petli@lysator.liu.se> 1998
# Public Domain;  no copyright, no comments, no guarantees.

class Heap:
   EmptyError = 'EmptyError'
   
   def __init__(self):
      self.heap = []

   def insert(self, element):
      i = len(self.heap)
      self.heap.append(element)

      while i > 0:
	 p = (i - 1) / 2
	 if not self.heap[i] < self.heap[p]:
	    break
	 self.heap[i], self.heap[p] = self.heap[p], self.heap[i]
	 i = p

   def remove(self, element=None):
      if len(self.heap) == 0: raise Heap.EmptyError, 'Heap is empty'
      
      if element is None:
	 i = 0
      else:
	 try:
	    i = self.heap.index(element)
	 except ValueError:
	    raise ValueError, 'Heap.remove(x): x not in heap'
	 
      e = self.heap[i]
      self.__removeindex__(i)
      return e

   def empty(self):
      return len(self.heap) == 0

   def __removeindex__(self, i):
      self.heap[i] = self.heap[-1]
      del self.heap[-1]

      while 1:
	 le = 2 * i + 1
	 if le + 1 < len(self.heap):
	    if (self.heap[le] < self.heap[le + 1]
		and self.heap[le] < self.heap[i]):
	       self.heap[i], self.heap[le] = self.heap[le], self.heap[i]
	       i = le
	    elif self.heap[le + 1] < self.heap[i]:
	       self.heap[i], self.heap[le + 1] = \
			     self.heap[le + 1], self.heap[i]
	       i = le + 1
	    else:
	       break
	 elif le < len(self.heap) and self.heap[le] < self.heap[i]:
	     self.heap[i], self.heap[le] = self.heap[le], self.heap[i]
	     break
	 else:
	    break

   def __len__(self):
      return len(self.heap)

   def __getitem__(self, i):
      return self.heap[i]
   
	 
